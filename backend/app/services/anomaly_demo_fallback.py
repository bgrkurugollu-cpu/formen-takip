from __future__ import annotations

from app.models.anomaly import Anomaly
from app.models.enums import AnomalyType
from app.services.anomaly_kpi_defs import ANOMALY_TYPE_LABELS, SEVERITY_LABELS

_CAUSE_POOL: dict[AnomalyType, list[dict]] = {
    AnomalyType.SHIFT_UNDERPERFORMANCE: [
        {"cause": "Vardiyalar arası ekipman/hat ayar farkı", "confidence": "medium"},
        {"cause": "Vardiya koşullarında (aydınlatma, sıcaklık, personel deneyimi) farklılık", "confidence": "low"},
    ],
    AnomalyType.RISING_TREND: [
        {"cause": "Hammadde parti kalitesinde kademeli değişim", "confidence": "medium"},
        {"cause": "Ekipman aşınmasına bağlı kademeli performans düşüşü", "confidence": "medium"},
    ],
    AnomalyType.FOREMAN_DEVIATION: [
        {"cause": "Vardiya bazlı süreç uygulama farklılıkları", "confidence": "low"},
        {"cause": "Ekip/personel devir hızındaki farklılıklar", "confidence": "low"},
    ],
    AnomalyType.PRODUCT_GROUP_DEVIATION: [
        {"cause": "Ürün grubuna özgü format/kalıp uyumsuzluğu", "confidence": "medium"},
        {"cause": "Ürün grubu reçetesinde yakın zamanlı değişiklik", "confidence": "low"},
    ],
    AnomalyType.DOWNTIME_CONCENTRATION: [
        {"cause": "Belirli saatlerde tekrarlayan teknik arıza", "confidence": "high"},
        {"cause": "Planlı bakım programının duruşlarla çakışması", "confidence": "medium"},
    ],
    AnomalyType.PLAN_ADHERENCE_STREAK: [
        {"cause": "Üretim planının güncel kapasiteyle uyumsuzluğu", "confidence": "medium"},
        {"cause": "Malzeme/hammadde tedarikinde gecikme", "confidence": "low"},
    ],
    AnomalyType.PLANT_HISTORICAL_DEVIATION: [
        {"cause": "Tesise özgü süreç veya ekipman değişikliği", "confidence": "medium"},
        {"cause": "Mevsimsel veya ürün karması kaynaklı değişim", "confidence": "low"},
    ],
    AnomalyType.CROSS_PLANT_GAP: [
        {"cause": "Tesisler arası ekipman yaşı veya kapasite farkı", "confidence": "medium"},
        {"cause": "En iyi uygulamaların tesisler arasında standardize edilmemiş olması", "confidence": "low"},
    ],
    AnomalyType.MULTI_KPI_SIMULTANEOUS: [
        {"cause": "Ortak kök neden (ör. hat durması) birden çok KPI'ı etkilemiş olabilir", "confidence": "medium"},
        {"cause": "Vardiya genelinde geçerli tek bir operasyonel sorun", "confidence": "medium"},
    ],
    AnomalyType.SINGLE_DAY_SPIKE: [
        {"cause": "Tek seferlik ekipman arızası veya kalibrasyon hatası", "confidence": "medium"},
        {"cause": "Veri girişinde tek günlük anomali (ölçüm/aktarım hatası olasılığı)", "confidence": "low"},
    ],
    AnomalyType.CHRONIC_ANOMALY: [
        {"cause": "Kalıcı hale gelmiş bir süreç veya ekipman sorunu", "confidence": "high"},
        {"cause": "Kök nedenin daha önce giderilmemiş olması", "confidence": "medium"},
    ],
    AnomalyType.CRITICAL_PRODUCTION_LOSS: [
        {"cause": "Kritik ekipman arızası veya büyük çaplı duruş", "confidence": "high"},
        {"cause": "Planlama veya tedarik zincirinde ciddi aksama", "confidence": "medium"},
    ],
    AnomalyType.DATA_QUALITY_SUSPECT: [
        {"cause": "Kaynak sistemden gecikmeli veya eksik veri aktarımı", "confidence": "high"},
        {"cause": "Gerçek bir operasyonel sorundan çok veri kalitesi sorunu olabilir", "confidence": "medium"},
    ],
}

_RESPONSIBLE_UNITS = ["Üretim", "Kalite", "Bakım", "Planlama"]


def generate_demo_analysis(anomaly: Anomaly, package: dict) -> dict:
    label = ANOMALY_TYPE_LABELS[anomaly.anomaly_type]
    severity_label = SEVERITY_LABELS[anomaly.severity.value]
    plant_name = package["anomaly"]["plant_name"] or "İlgili tesis"
    shift_name = package["anomaly"]["shift_name"]
    kpi_name = package["kpi_definition"]["name"] or "İlgili KPI"
    deviation = package["anomaly"]["deviation_percent"]

    shift_part = f" {shift_name} vardiyasında" if shift_name else ""
    executive_summary = (
        f"{plant_name} tesisinde{shift_part} {kpi_name} göstergesinde {label.lower()} niteliğinde, "
        f"%{deviation} sapma içeren {severity_label.lower()} önem düzeyinde bir tespit tanımlanmıştır. "
        f"Bu özet, otomatik demo analiz modunda üretilmiştir ve yönetici incelemesi gerektirir."
    )

    verified_findings = [
        {"finding": e["label"], "evidence": f"{e['value']} {e['unit']}"} for e in package["anomaly"]["evidence"]
    ]

    causes = _CAUSE_POOL.get(anomaly.anomaly_type, [])
    possible_causes = [
        {
            "cause": c["cause"],
            "confidence": c["confidence"],
            "supporting_evidence": [f"Gözlenen sapma %{deviation} olarak ölçülmüştür."],
            "contradicting_evidence": [],
            "verification_required": "Saha ekibi tarafından yerinde doğrulama ve ilgili kayıtların incelenmesi gerekir.",
        }
        for c in causes
    ]

    priority = {"low": "low", "medium": "medium", "high": "high", "critical": "critical"}[anomaly.severity.value]
    recommended_investigations = [
        {
            "step": f"{kpi_name} için {plant_name} sahasında yerinde inceleme yapılması",
            "responsible_unit": "Üretim",
            "priority": priority,
            "expected_output": "Kök nedenin doğrulanması veya dışlanması",
        },
        {
            "step": "İlgili dönemdeki bakım ve duruş kayıtlarının incelenmesi",
            "responsible_unit": "Bakım",
            "priority": "medium",
            "expected_output": "Teknik/imalat kaynaklı bir neden olup olmadığının netleştirilmesi",
        },
    ]

    immediate_actions = [
        {
            "action": f"{plant_name} sahasında {kpi_name} göstergesinin yakın takibe alınması",
            "responsible_unit": "Üretim",
            "priority": priority,
            "timeframe": "1-2 gün içinde",
            "expected_impact": "Anormalliğin devam edip etmediğinin doğrulanması",
            "requires_approval": True,
        }
    ]

    medium_term_actions = [
        {
            "action": "Süreç standardizasyonu ve ekip bilgilendirme toplantısı planlanması",
            "responsible_unit": "Planlama",
            "expected_impact": "Benzer sapmaların tekrarlanma olasılığının azaltılması",
        }
    ]

    missing_information = [
        "Vardiya bazlı ekip deneyim/eğitim durumu bu pakette yer almamaktadır.",
        "İlgili dönemdeki hammadde tedarikçi/parti bilgisi doğrulanmamıştır.",
    ]

    analysis_confidence = round(max(0.35, min(0.9, float(anomaly.ml_confidence) - 0.1)), 2)

    return {
        "executive_summary": executive_summary,
        "verified_findings": verified_findings,
        "possible_causes": possible_causes,
        "recommended_investigations": recommended_investigations,
        "immediate_actions": immediate_actions,
        "medium_term_actions": medium_term_actions,
        "missing_information": missing_information,
        "risk_level": anomaly.severity.value,
        "analysis_confidence": analysis_confidence,
        "requires_human_review": True,
        "disclaimer": (
            "Bu analiz demo modunda otomatik olarak üretilmiştir; gerçek bir yapay zekâ modeli "
            "tarafından oluşturulmamıştır. Tüm bulgular ve öneriler yönetici onayı ve saha "
            "doğrulaması gerektirir; üretim sisteminde otomatik bir işlem tetiklenmemiştir."
        ),
    }
