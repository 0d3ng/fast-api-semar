import json
import unittest
from unittest.mock import AsyncMock, patch

from app.schemas.firmware_release_schema import LatestFirmwareReleaseResponse, FirmwareReleaseResponse
from app.schemas.rotation_request_schema import CurrentKeyGenerationResponse
from app.services.firmware_release_service import FirmwareReleaseService
from app.services.rotation_request_service import RotationRequestService
from app.utils.config import SEMAR_API_TOKEN
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestCicdEndpoints(unittest.IsolatedAsyncioTestCase):

    def test_key_generation_current_unauthorized(self):
        response = client.get("/api/v1/key-generation/current", headers={"Authorization": "Bearer invalid_token"})
        self.assertEqual(response.status_code, 401)

    def test_firmware_release_latest_unauthorized(self):
        response = client.get("/api/v1/firmware-releases/latest", headers={"Authorization": "Bearer invalid_token"})
        self.assertEqual(response.status_code, 401)

    def test_firmware_release_create_unauthorized(self):
        response = client.post("/api/v1/firmware-releases/", data={"manifest": "{}"}, headers={"Authorization": "Bearer invalid_token"})
        self.assertEqual(response.status_code, 401)

    @patch("app.routes.firmware_release_routes.FirmwareReleaseService.create_release")
    def test_firmware_release_create_success(self, mock_create_release):
        from bson import ObjectId
        mock_response = FirmwareReleaseResponse(
            _id=ObjectId("6774d10911eccac1be83544d"),
            target_version="v1.2.3",
            base_version="v1.2.2",
            type="full",
            target_hash="hash",
            target_size=100,
            key_generation=1,
            signature="signature",
            inserted_at="2026-08-16T13:46:00Z",
            inserted_by="system"
        )
        
        async def mock_async_call(*args, **kwargs):
            return mock_response
            
        mock_create_release.side_effect = mock_async_call
        
        manifest_data = {
            "target_version": "v1.2.3",
            "base_version": "v1.2.2",
            "type": "full",
            "target_hash": "hash",
            "target_size": 100,
            "key_generation": 1,
            "signature": "signature"
        }
        
        response = client.post(
            "/api/v1/firmware-releases/",
            data={"manifest": json.dumps(manifest_data)},
            headers={"Authorization": f"Bearer {SEMAR_API_TOKEN}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["target_version"], "v1.2.3")


    @patch("app.services.rotation_request_service.db")
    async def test_get_current_key_generation_found(self, mock_db):
        mock_db.rotation_requests.find_one = AsyncMock(return_value={"new_key_generation": 5})
        res = await RotationRequestService.get_current_key_generation()
        self.assertIsInstance(res, CurrentKeyGenerationResponse)
        self.assertEqual(res.key_generation, 5)

    @patch("app.services.rotation_request_service.db")
    async def test_get_current_key_generation_none(self, mock_db):
        mock_db.rotation_requests.find_one = AsyncMock(return_value=None)
        res = await RotationRequestService.get_current_key_generation()
        self.assertIsInstance(res, CurrentKeyGenerationResponse)
        self.assertEqual(res.key_generation, 0)

    @patch("app.services.firmware_release_service.db")
    async def test_get_latest_release_found(self, mock_db):
        mock_db.firmware_releases.find_one = AsyncMock(return_value={
            "target_version": "v1.2.3",
            "type": "full",
            "inserted_at": "2026-08-12T10:00:00Z"
        })
        res = await FirmwareReleaseService.get_latest_release(release_type="full")
        self.assertIsInstance(res, LatestFirmwareReleaseResponse)
        self.assertEqual(res.target_version, "v1.2.3")
        self.assertEqual(res.type, "full")
        self.assertEqual(res.created_at, "2026-08-12T10:00:00Z")

    @patch("app.services.firmware_release_service.db")
    async def test_get_latest_release_none(self, mock_db):
        mock_db.firmware_releases.find_one = AsyncMock(return_value=None)
        res = await FirmwareReleaseService.get_latest_release(release_type="full")
        self.assertIsInstance(res, LatestFirmwareReleaseResponse)
        self.assertIsNone(res.target_version)
        self.assertIsNone(res.type)
        self.assertIsNone(res.created_at)


if __name__ == '__main__':
    unittest.main()
