from datetime import datetime
from typing import Optional, List, Union, Any, Dict
import pytz
from bson import ObjectId
from fastapi import HTTPException
from starlette import status as http_status

from app.models.ota_network_metric import OtaNetworkMetric, DeviceNetworkMetric, NetworkMetricSummary
from app.schemas.ota_network_metric_schema import (
    OtaNetworkMetricCreate,
    OtaNetworkMetricResponse,
    ProtocolComparisonItem,
    NetworkComparisonResponse
)
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OtaNetworkMetricService:

    @staticmethod
    async def record_metrics(
        session_id: Union[int, str],
        metric_in: OtaNetworkMetricCreate,
        user_id: str = "system"
    ) -> OtaNetworkMetricResponse:
        try:
            now_utc = datetime.now(tz=pytz.UTC)

            # 1. Resolve session from ota_update_sessions
            query = {"deleted_at": None}
            if isinstance(session_id, str) and ObjectId.is_valid(session_id):
                query["$or"] = [{"_id": ObjectId(session_id)}, {"session_id": session_id}]
            else:
                try:
                    s_id_int = int(session_id)
                    query["$or"] = [{"session_id": s_id_int}, {"session_id": str(session_id)}]
                except (ValueError, TypeError):
                    query["session_id"] = session_id

            session = await db.ota_update_sessions.find_one(query)

            resolved_edge_id = metric_in.edge_id
            session_duration = metric_in.summary.duration_seconds
            firmware_size = metric_in.firmware_size_bytes or 0

            if session:
                if not resolved_edge_id:
                    resolved_edge_id = str(session.get("target_edge_ota_id", "unknown"))
                if session_duration is None or session_duration == 0:
                    session_duration = session.get("duration_seconds")
                raw_session_id = session.get("session_id", session_id)
            else:
                raw_session_id = session_id
                if not resolved_edge_id:
                    resolved_edge_id = "unknown"

            # 2. Enrich per-device metrics with ota_session_acks data (Single Source of Truth)
            acks_map: Dict[str, dict] = {}
            if session:
                sess_obj_id = str(session.get("_id"))
                acks_cursor = db.ota_session_acks.find({
                    "update_session_id": sess_obj_id,
                    "deleted_at": None
                })
                async for ack in acks_cursor:
                    dev_id = str(ack.get("end_device_id"))
                    acks_map[dev_id] = ack

            enriched_devices: List[DeviceNetworkMetric] = []
            for dev in (metric_in.devices_metrics or []):
                target_id = str(dev.device_id or dev.end_device_id or "")
                ack_info = acks_map.get(target_id)
                dev_status = dev.ack_status
                dev_ms = dev.total_duration_ms
                dev_sec = dev.duration_seconds

                if ack_info:
                    if not dev_status or dev_status == "unknown":
                        dev_status = ack_info.get("status", "unknown")
                    if dev_ms is None and ack_info.get("total_duration_ms") is not None:
                        dev_ms = ack_info.get("total_duration_ms")

                # Conversion: ms -> seconds
                if dev_ms is not None and (dev_sec is None or dev_sec == 0):
                    dev_sec = round(float(dev_ms) / 1000.0, 2)

                enriched_devices.append(
                    DeviceNetworkMetric(
                        device_id=target_id,
                        ack_status=dev_status,
                        total_duration_ms=dev_ms,
                        duration_seconds=dev_sec,
                        tx_bytes=dev.tx_bytes,
                        rx_bytes=dev.rx_bytes,
                        total_bytes=dev.total_bytes or (dev.tx_bytes + dev.rx_bytes),
                        chunks_sent=dev.chunks_sent,
                        chunks_retransmitted=dev.chunks_retransmitted,
                        nack_count=dev.nack_count
                    )
                )

            summary = NetworkMetricSummary(
                total_tx_bytes=metric_in.summary.total_tx_bytes,
                total_rx_bytes=metric_in.summary.total_rx_bytes,
                total_load_bytes=metric_in.summary.total_load_bytes or (metric_in.summary.total_tx_bytes + metric_in.summary.total_rx_bytes),
                duration_seconds=session_duration
            )

            dev_count = metric_in.devices_count or metric_in.device_count or len(enriched_devices) or 1

            metric_doc = OtaNetworkMetric(
                session_id=raw_session_id,
                edge_id=str(resolved_edge_id),
                devices_count=dev_count,
                protocol=metric_in.protocol.lower(),
                firmware_size_bytes=firmware_size,
                summary=summary,
                tx_breakdown=metric_in.tx_breakdown,
                rx_breakdown=metric_in.rx_breakdown,
                devices_metrics=enriched_devices,
                inserted_at=now_utc,
                inserted_by=user_id
            )

            doc_dict = metric_doc.model_dump(by_alias=True)

            # Upsert into db.ota_network_metrics
            filter_query = {
                "$or": [
                    {"session_id": raw_session_id},
                    {"session_id": str(raw_session_id)}
                ],
                "deleted_at": None
            }
            existing = await db.ota_network_metrics.find_one(filter_query)
            if existing:
                doc_dict.pop("_id", None)
                doc_dict["updated_at"] = now_utc
                doc_dict["updated_by"] = user_id
                await db.ota_network_metrics.update_one(
                    {"_id": existing["_id"]},
                    {"$set": doc_dict}
                )
                metric_id = existing["_id"]
                logger.info(f"[NETWORK_METRICS] Updated network metrics for session {session_id} (id={metric_id})")
            else:
                res = await db.ota_network_metrics.insert_one(doc_dict)
                metric_id = res.inserted_id
                logger.info(f"[NETWORK_METRICS] Inserted new network metrics for session {session_id} (id={metric_id})")

            saved_doc = await db.ota_network_metrics.find_one({"_id": metric_id})
            return OtaNetworkMetricResponse(**saved_doc)

        except Exception as e:
            logger.error(f"Failed to record network metrics: {e}", exc_info=True)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to record network metrics: {str(e)}"
            )

    @staticmethod
    async def get_metrics_by_session(session_id: Union[int, str]) -> OtaNetworkMetricResponse:
        query = {"deleted_at": None}
        if isinstance(session_id, str) and ObjectId.is_valid(session_id):
            query["$or"] = [
                {"_id": ObjectId(session_id)},
                {"session_id": session_id}
            ]
        else:
            try:
                s_int = int(session_id)
                query["$or"] = [{"session_id": s_int}, {"session_id": str(session_id)}]
            except (ValueError, TypeError):
                query["session_id"] = session_id

        doc = await db.ota_network_metrics.find_one(query)
        if not doc:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Network metrics for session '{session_id}' not found"
            )
        return OtaNetworkMetricResponse(**doc)

    @staticmethod
    async def get_comparison_metrics(
        session_ids: Optional[List[str]] = None,
        edge_id: Optional[str] = None
    ) -> NetworkComparisonResponse:
        query: Dict[str, Any] = {"deleted_at": None}
        if session_ids:
            s_queries = []
            for s in session_ids:
                s_queries.append(s)
                try:
                    s_queries.append(int(s))
                except (ValueError, TypeError):
                    pass
                if ObjectId.is_valid(s):
                    s_queries.append(ObjectId(s))
            query["session_id"] = {"$in": s_queries}

        if edge_id:
            query["edge_id"] = edge_id

        cursor = db.ota_network_metrics.find(query).sort("inserted_at", -1)
        items: List[ProtocolComparisonItem] = []

        async for doc in cursor:
            summary = doc.get("summary", {})
            tx = summary.get("total_tx_bytes", 0)
            rx = summary.get("total_rx_bytes", 0)
            total = summary.get("total_load_bytes", tx + rx)
            duration = summary.get("duration_seconds")
            fw_size = doc.get("firmware_size_bytes", 0)
            devs = doc.get("devices_metrics", [])
            dev_count = len(devs)

            # Repair/retransmit calculation
            tx_breakdown = doc.get("tx_breakdown", {})
            repair_bytes = tx_breakdown.get("repair_bytes", 0)
            if not repair_bytes:
                # Sum from devices
                repair_bytes = sum(d.get("chunks_retransmitted", 0) * 512 for d in devs)

            retrans_ratio = round((repair_bytes / total * 100.0), 2) if total > 0 else 0.0

            # Wire Amplification Factor (WAF) = Total TX / (Firmware Size)
            waf = round(float(tx) / float(fw_size), 2) if fw_size > 0 else 0.0

            # Throughput in KB/s
            throughput = 0.0
            if duration and duration > 0:
                throughput = round((total / 1024.0) / duration, 2)

            items.append(
                ProtocolComparisonItem(
                    session_id=doc.get("session_id"),
                    protocol=doc.get("protocol", "unknown"),
                    edge_id=doc.get("edge_id", "unknown"),
                    firmware_size_bytes=fw_size,
                    devices_count=dev_count,
                    duration_seconds=duration,
                    total_tx_bytes=tx,
                    total_rx_bytes=rx,
                    total_load_bytes=total,
                    retransmission_bytes=repair_bytes,
                    retransmission_ratio_pct=retrans_ratio,
                    wire_amplification_factor=waf,
                    throughput_kbps=throughput
                )
            )

        # Build protocol summary aggregations
        proto_summary: Dict[str, Any] = {}
        for it in items:
            p = it.protocol
            if p not in proto_summary:
                proto_summary[p] = {
                    "count": 0,
                    "avg_total_load_bytes": 0,
                    "avg_duration_seconds": 0.0,
                    "avg_waf": 0.0,
                    "avg_throughput_kbps": 0.0
                }
            proto_summary[p]["count"] += 1
            proto_summary[p]["avg_total_load_bytes"] += it.total_load_bytes
            proto_summary[p]["avg_duration_seconds"] += (it.duration_seconds or 0.0)
            proto_summary[p]["avg_waf"] += it.wire_amplification_factor
            proto_summary[p]["avg_throughput_kbps"] += it.throughput_kbps

        for p, s in proto_summary.items():
            c = s["count"]
            if c > 0:
                s["avg_total_load_bytes"] = round(s["avg_total_load_bytes"] / c, 2)
                s["avg_duration_seconds"] = round(s["avg_duration_seconds"] / c, 2)
                s["avg_waf"] = round(s["avg_waf"] / c, 2)
                s["avg_throughput_kbps"] = round(s["avg_throughput_kbps"] / c, 2)

        return NetworkComparisonResponse(
            sessions=items,
            summary=proto_summary
        )
