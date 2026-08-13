import unittest
from unittest.mock import AsyncMock, patch

from app.schemas.firmware_release_schema import LatestFirmwareReleaseResponse
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
