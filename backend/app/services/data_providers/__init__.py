"""Aktif veri sağlayıcı paketini döndüren tek fabrika noktası.

Bugün her zaman sentetik implementasyonları döndürür. İleride gerçek Ocean/ML servisleri
eklendiğinde, yalnızca bu fonksiyonun içi (hangi sınıfın örnekleneceği) değişir — tool
tanımları (`app/services/tools/definitions.py`) ve LLM'e sunulan araç şemaları hiç değişmez,
çünkü hepsi `base.py`'deki soyut arayüzlere karşı yazılmıştır."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.services.data_providers.base import (
    AnomalyDataProvider,
    DowntimeDataProvider,
    HistoricalCaseDataProvider,
    KPIDataProvider,
    MaintenanceDataProvider,
    ProductDataProvider,
    ShiftDataProvider,
)
from app.services.data_providers.synthetic import (
    SyntheticAnomalyDataProvider,
    SyntheticDowntimeDataProvider,
    SyntheticHistoricalCaseDataProvider,
    SyntheticKPIDataProvider,
    SyntheticMaintenanceDataProvider,
    SyntheticProductDataProvider,
    SyntheticShiftDataProvider,
)


@dataclass
class ProviderBundle:
    anomaly: AnomalyDataProvider
    kpi: KPIDataProvider
    downtime: DowntimeDataProvider
    maintenance: MaintenanceDataProvider
    product: ProductDataProvider
    shift: ShiftDataProvider
    historical: HistoricalCaseDataProvider


def get_data_providers(db: Session) -> ProviderBundle:
    return ProviderBundle(
        anomaly=SyntheticAnomalyDataProvider(db),
        kpi=SyntheticKPIDataProvider(db),
        downtime=SyntheticDowntimeDataProvider(db),
        maintenance=SyntheticMaintenanceDataProvider(db),
        product=SyntheticProductDataProvider(db),
        shift=SyntheticShiftDataProvider(db),
        historical=SyntheticHistoricalCaseDataProvider(db),
    )
