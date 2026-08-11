
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
