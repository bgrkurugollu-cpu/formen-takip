
from __future__ import annotations

import argparse
import random
import sys
from datetime import date, datetime, timedelta

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User
from app.services.ingestion import backfill_data_quality_issues, run_ingestion
from app.services.providers.synthetic_provider import SyntheticDataProvider
from app.services.rescoring import apply_scoring_model_v2
from app.services.synthetic.anomaly_generator import seed_anomalies
from app.services.synthetic.contribution_generator import seed_contribution_works
from app.services.synthetic.production_generator import GenerationParams, seed_production_data
from app.services.synthetic.reference_data import regenerate_personnel_identities, seed_reference_data


def cmd_seed(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    period_end = date.fromisoformat(args.end_date) if args.end_date else date.today()
    period_start = date.fromisoformat(args.start_date) if args.start_date else period_end - timedelta(days=365)

    db = SessionLocal()
    try:
        from sqlalchemy import select

        from app.models.organization import Plant

        existing = db.scalar(select(Plant).limit(1))
        if existing and not args.force:
            print("Referans veri zaten mevcut. Yeniden oluşturmak için --force kullanın.")
            sys.exit(1)

        print(f"[1/3] Referans veri + KPI hedefleri üretiliyor (seed={args.seed})...")
        ref = seed_reference_data(
            db, rng,
            min_plants_per_foreman=args.min_plants_per_foreman,
            max_plants_per_foreman=args.max_plants_per_foreman,
            period_start=period_start,
            period_end=period_end,
        )
        print(
            f"  -> {len(ref.factories)} fabrika, {len(ref.plants)} tesis, {len(ref.chiefs)} şef, "
            f"{len(ref.foremen)} formen, {len(ref.kpis)} KPI oluşturuldu."
        )

        print(f"[2/3] Üretim verisi üretiliyor ({period_start} -> {period_end})...")
        params = GenerationParams(
            missing_rate=args.missing_rate,
            error_rate=args.error_rate,
            anomaly_rate=args.anomaly_rate,
            duplicate_rate=args.duplicate_rate,
        )
        production = seed_production_data(db, rng, ref, period_start, period_end, params)
        print(
            f"  -> {len(production.products)} ürün, "
            f"{sum(len(v) for v in production.lines_by_plant.values())} hat, "
            f"{len(production.work_calendar)} çalışma takvimi kaydı, "
            f"{len(production.production_records)} üretim kaydı oluşturuldu."
        )

        print("[3/3] KPI türetme ve ingestion çalıştırılıyor...")
        provider = SyntheticDataProvider(db, rng, duplicate_rate=args.duplicate_rate)
        run = run_ingestion(db, provider, period_start, period_end, plant_codes=[p.code for p in ref.plants])
        print(
            f"  -> İşlenen: {run.processed_count}, başarılı: {run.success_count}, "
            f"atlanan (tekrar): {run.skipped_count}, hatalı: {run.error_count}, durum: {run.status.value}"
        )

        admin = db.scalar(select(User).order_by(User.created_at).limit(1))
        if admin:
            print("[4/4] Katkı ve iyileştirme çalışmaları örnek verisi üretiliyor...")
            contrib = seed_contribution_works(db, rng, admin.id, count=40)
            print(
                f"  -> {contrib.works_created} çalışma oluşturuldu "
                f"({contrib.published_count} yayımlandı, {contrib.draft_count} taslak)."
            )
        else:
            print("[4/5] Kullanıcı bulunamadığı için katkı çalışması örneği atlandı (önce create-admin çalıştırın).")

        print("[5/5] Sentetik ML tespitleri (Tespitler modülü) üretiliyor...")
        anomalies = seed_anomalies(db, rng)
        print(f"  -> {anomalies.anomalies_created} tespit oluşturuldu.")
    finally:
        db.close()


def cmd_create_admin(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        from sqlalchemy import select

        existing = db.scalar(select(User).where(User.email == args.email))
        if existing:
            print(f"Kullanıcı zaten mevcut: {args.email}")
            return
        user = User(
            email=args.email,
            password_hash=hash_password(args.password),
            full_name=args.full_name,
            title="Genel Müdür",
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Üst yönetim kullanıcısı oluşturuldu: {args.email}")
    finally:
        db.close()


def cmd_backfill_data_quality(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        print("Eksik veri kalitesi kayıtları taranıyor (COMPLETE olmayan ama issue'su bulunmayan kayıtlar)...")
        total = backfill_data_quality_issues(db)
        print(f"  -> {total} yeni data_quality_issues kaydı oluşturuldu.")
    finally:
        db.close()


def cmd_apply_scoring_model_v2(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        print("[1/3] AGIR_GITME actual/numerator/denominator yeni (bant bazlı, işaretli) türetimle yeniden hesaplanıyor...")
        result = apply_scoring_model_v2(db)
        ag = result["agir_gitme_actuals"]
        print(f"  -> güncellenen: {ag['updated']}, atlanan: {ag['skipped']}")

        print("[2/3] INKITA (Teknik+İmalat) için geriye dönük ingestion tamamlandı.")
        ik = result["inkita_backfill"]
        print(f"  -> işlenen: {ik['processed']}, başarılı: {ik['success']}, atlanan: {ik['skipped']}, hatalı: {ik['error']}")

        print("[3/3] Tüm performance_scores aktif kurallarla yeniden hesaplandı.")
        rs = result["rescore_all"]
        print(f"  -> güncellenen: {rs['updated']}, atlanan: {rs['skipped']}")
    finally:
        db.close()


def cmd_seed_contributions(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        from sqlalchemy import select

        admin = db.scalar(select(User).order_by(User.created_at).limit(1))
        if not admin:
            print("Kullanıcı bulunamadı. Önce create-admin çalıştırın.")
            sys.exit(1)
        print(f"Katkı ve iyileştirme çalışmaları örnek verisi üretiliyor (seed={args.seed}, count={args.count})...")
        result = seed_contribution_works(db, random.Random(args.seed), admin.id, count=args.count)
        print(
            f"  -> {result.works_created} çalışma oluşturuldu "
            f"({result.published_count} yayımlandı, {result.draft_count} taslak)."
        )
    finally:
        db.close()


def cmd_seed_anomalies(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        print(f"Sentetik ML tespitleri üretiliyor (seed={args.seed})...")
        result = seed_anomalies(db, random.Random(args.seed))
        print(f"  -> {result.anomalies_created} tespit oluşturuldu (zaten var olan kodlar atlandı).")
    finally:
        db.close()


def cmd_regenerate_personnel(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        print("Şef/formen ad-soyad ve sicil numaraları yeniden üretiliyor (performans verisine dokunulmaz)...")
        chiefs, foremen = regenerate_personnel_identities(db, random.Random(args.seed))
        print(f"  -> {chiefs} şef, {foremen} formen güncellendi.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    seed_parser = sub.add_parser("seed", help="Organizasyon + sentetik performans verisi üretir")
    seed_parser.add_argument("--seed", type=int, default=42)
    seed_parser.add_argument("--min-plants-per-foreman", type=int, default=2)
    seed_parser.add_argument("--max-plants-per-foreman", type=int, default=4)
    seed_parser.add_argument("--start-date", type=str, default=None, help="YYYY-MM-DD")
    seed_parser.add_argument("--end-date", type=str, default=None, help="YYYY-MM-DD")
    seed_parser.add_argument("--missing-rate", type=float, default=0.02)
    seed_parser.add_argument("--error-rate", type=float, default=0.01)
    seed_parser.add_argument("--anomaly-rate", type=float, default=0.015)
    seed_parser.add_argument("--duplicate-rate", type=float, default=0.005)
    seed_parser.add_argument("--force", action="store_true", help="Referans veri mevcutsa bile devam et")
    seed_parser.set_defaults(func=cmd_seed)

    admin_parser = sub.add_parser("create-admin", help="Üst yönetim demo kullanıcısı oluşturur")
    admin_parser.add_argument("--email", type=str, default="genel.mudur@formen-demo.com")
    admin_parser.add_argument("--password", type=str, default="Demo!2026")
    admin_parser.add_argument("--full-name", type=str, default="Demo Genel Müdür")
    admin_parser.set_defaults(func=cmd_create_admin)

    regen_parser = sub.add_parser(
        "regenerate-personnel-identities",
        help="Var olan şef/formen kayıtlarının ad-soyad ve sicil numaralarını benzersiz olacak şekilde yeniden üretir",
    )
    regen_parser.add_argument("--seed", type=int, default=42)
    regen_parser.set_defaults(func=cmd_regenerate_personnel)

    backfill_parser = sub.add_parser(
        "backfill-data-quality-issues", help="Faz 1'de üretilmiş kayıtlar için geriye dönük veri kalitesi sorunu kayıtları oluşturur"
    )
    backfill_parser.set_defaults(func=cmd_backfill_data_quality)

    scoring_v2_parser = sub.add_parser(
        "apply-scoring-model-v2",
        help="Mevcut performans verisini KPI'a özel yeni puanlama formülleriyle yeniden hesaplar "
        "(AGIR_GITME işaretli türetim düzeltmesi + INKITA geriye dönük ingestion + tüm skorların yeniden hesaplanması)",
    )
    scoring_v2_parser.set_defaults(func=cmd_apply_scoring_model_v2)

    contrib_parser = sub.add_parser(
        "seed-contributions",
        help="Var olan tesis/formen verisine dayalı katkı ve iyileştirme çalışması örnekleri üretir "
        "(tam yeniden seed gerekmeden mevcut veritabanına eklenebilir)",
    )
    contrib_parser.add_argument("--seed", type=int, default=42)
    contrib_parser.add_argument("--count", type=int, default=40)
    contrib_parser.set_defaults(func=cmd_seed_contributions)

    anomalies_parser = sub.add_parser(
        "seed-anomalies",
        help="Tespitler modülü için sabit senaryo kataloğundan sentetik ML tespitleri üretir "
        "(zaten var olan tespit kodları atlanır, tekrar çalıştırmak güvenlidir)",
    )
    anomalies_parser.add_argument("--seed", type=int, default=42)
    anomalies_parser.set_defaults(func=cmd_seed_anomalies)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
