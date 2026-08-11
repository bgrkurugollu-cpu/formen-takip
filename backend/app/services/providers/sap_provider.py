
from __future__ import annotations

from collections.abc import Iterator
from datetime import date

from app.core.config import get_settings
from app.models.enums import SourceSystem
from app.services.providers.base import PerformanceDataProvider, RawPerformanceRecord


class SAPNotConfiguredError(RuntimeError):
    pass


class SAPDataProvider(PerformanceDataProvider):
    source_system = SourceSystem.SAP

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.sap_base_url
        self._client_id = settings.sap_client_id
        self._client_secret = settings.sap_client_secret

    def fetch(
        self,
        date_from: date,
        date_to: date,
        plant_codes: list[str] | None = None,
    ) -> Iterator[RawPerformanceRecord]:
        if not self._base_url:
            raise SAPNotConfiguredError(
                "SAP bağlantısı yapılandırılmamış. Bu sağlayıcı, gerçek SAP entegrasyonu "
                "(OData/BAPI/IDoc/Integration Suite) uygulandığında SAP_BASE_URL, "
                "SAP_CLIENT_ID, SAP_CLIENT_SECRET ortam değişkenleri ile aktifleştirilecektir."
            )
        raise NotImplementedError("SAP entegrasyonu henüz implement edilmedi.")
