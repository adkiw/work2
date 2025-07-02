from sqlalchemy.orm import Session
from uuid import UUID
from . import models, schemas, auth
import json
from datetime import datetime


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        email=user.email,
        hashed_password=auth.hash_password(user.password),
        full_name=user.full_name,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, user_id: UUID) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()


def create_audit_log(
    db: Session, user_id: UUID | None, data: schemas.AuditLogCreate
) -> models.AuditLog:
    log = models.AuditLog(
        user_id=user_id,
        action=data.action,
        table_name=data.table_name,
        record_id=data.record_id,
        timestamp=datetime.utcnow(),
        details=(
            json.dumps(data.details, ensure_ascii=False)
            if data.details is not None
            else None
        ),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_audit_logs(
    db: Session,
    limit: int = 100,
    user_id: UUID | None = None,
    table_name: str | None = None,
    action: str | None = None,
) -> list[models.AuditLog]:
    query = db.query(models.AuditLog)
    if user_id:
        query = query.filter(models.AuditLog.user_id == user_id)
    if table_name:
        query = query.filter(models.AuditLog.table_name == table_name)
    if action:
        query = query.filter(models.AuditLog.action == action)
    return (
        query.order_by(models.AuditLog.timestamp.desc()).limit(limit).all()
    )


def create_shipment(
    db: Session, tenant_id: UUID, data: schemas.ShipmentCreate
) -> models.Shipment:
    shipment = models.Shipment(
        tenant_id=tenant_id,
        klientas=data.klientas,
        uzsakymo_numeris=data.uzsakymo_numeris,
        pakrovimo_data=data.pakrovimo_data,
        iskrovimo_data=data.iskrovimo_data,
        kilometrai=data.kilometrai,
        frachtas=data.frachtas,
        busena=data.busena,
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    return shipment


def update_shipment(
    db: Session, tenant_id: UUID, shipment_id: int, data: schemas.ShipmentCreate
) -> models.Shipment | None:
    shipment = (
        db.query(models.Shipment)
        .filter(
            models.Shipment.id == shipment_id,
            models.Shipment.tenant_id == tenant_id,
        )
        .first()
    )
    if not shipment:
        return None
    for field, value in data.dict().items():
        setattr(shipment, field, value)
    db.commit()
    db.refresh(shipment)
    return shipment


def delete_shipment(db: Session, tenant_id: UUID, shipment_id: int) -> bool:
    shipment = (
        db.query(models.Shipment)
        .filter(
            models.Shipment.id == shipment_id,
            models.Shipment.tenant_id == tenant_id,
        )
        .first()
    )
    if not shipment:
        return False
    db.delete(shipment)
    db.commit()
    return True


def get_shipments(db: Session, tenant_id: UUID) -> list[models.Shipment]:
    return (
        db.query(models.Shipment)
        .filter(models.Shipment.tenant_id == tenant_id)
        .order_by(models.Shipment.id.desc())
        .all()
    )

def create_truck(db: Session, tenant_id: UUID, data: schemas.TruckCreate) -> models.Truck:
    truck = models.Truck(
        tenant_id=tenant_id,
        numeris=data.numeris,
        marke=data.marke,
        pagaminimo_metai=data.pagaminimo_metai,
        tech_apziura=data.tech_apziura,
        draudimas=data.draudimas,
    )
    db.add(truck)
    db.commit()
    db.refresh(truck)
    return truck


def update_truck(db: Session, tenant_id: UUID, truck_id: int, data: schemas.TruckCreate) -> models.Truck | None:
    truck = (
        db.query(models.Truck)
        .filter(models.Truck.id == truck_id, models.Truck.tenant_id == tenant_id)
        .first()
    )
    if not truck:
        return None
    for field, value in data.dict().items():
        setattr(truck, field, value)
    db.commit()
    db.refresh(truck)
    return truck


def delete_truck(db: Session, tenant_id: UUID, truck_id: int) -> bool:
    truck = (
        db.query(models.Truck)
        .filter(models.Truck.id == truck_id, models.Truck.tenant_id == tenant_id)
        .first()
    )
    if not truck:
        return False
    db.delete(truck)
    db.commit()
    return True


def get_trucks(db: Session, tenant_id: UUID) -> list[models.Truck]:
    return (
        db.query(models.Truck)
        .filter(models.Truck.tenant_id == tenant_id)
        .order_by(models.Truck.id.desc())
        .all()
    )


def create_driver(db: Session, tenant_id: UUID, data: schemas.DriverCreate) -> models.Driver:
    driver = models.Driver(
        tenant_id=tenant_id,
        vardas=data.vardas,
        pavarde=data.pavarde,
        gimimo_metai=data.gimimo_metai,
        tautybe=data.tautybe,
        kadencijos_pabaiga=data.kadencijos_pabaiga,
        atostogu_pabaiga=data.atostogu_pabaiga,
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


def update_driver(db: Session, tenant_id: UUID, driver_id: int, data: schemas.DriverCreate) -> models.Driver | None:
    driver = (
        db.query(models.Driver)
        .filter(models.Driver.id == driver_id, models.Driver.tenant_id == tenant_id)
        .first()
    )
    if not driver:
        return None
    for field, value in data.dict().items():
        setattr(driver, field, value)
    db.commit()
    db.refresh(driver)
    return driver


def delete_driver(db: Session, tenant_id: UUID, driver_id: int) -> bool:
    driver = (
        db.query(models.Driver)
        .filter(models.Driver.id == driver_id, models.Driver.tenant_id == tenant_id)
        .first()
    )
    if not driver:
        return False
    db.delete(driver)
    db.commit()
    return True


def get_drivers(db: Session, tenant_id: UUID) -> list[models.Driver]:
    return (
        db.query(models.Driver)
        .filter(models.Driver.tenant_id == tenant_id)
        .order_by(models.Driver.id.desc())
        .all()
    )


def create_trailer(db: Session, tenant_id: UUID, data: schemas.TrailerCreate) -> models.Trailer:
    trailer = models.Trailer(
        tenant_id=tenant_id,
        numeris=data.numeris,
        priekabu_tipas=data.priekabu_tipas,
        marke=data.marke,
        pagaminimo_metai=data.pagaminimo_metai,
        tech_apziura=data.tech_apziura,
        draudimas=data.draudimas,
    )
    db.add(trailer)
    db.commit()
    db.refresh(trailer)
    return trailer


def update_trailer(db: Session, tenant_id: UUID, trailer_id: int, data: schemas.TrailerCreate) -> models.Trailer | None:
    trailer = (
        db.query(models.Trailer)
        .filter(models.Trailer.id == trailer_id, models.Trailer.tenant_id == tenant_id)
        .first()
    )
    if not trailer:
        return None
    for field, value in data.dict().items():
        setattr(trailer, field, value)
    db.commit()
    db.refresh(trailer)
    return trailer


def delete_trailer(db: Session, tenant_id: UUID, trailer_id: int) -> bool:
    trailer = (
        db.query(models.Trailer)
        .filter(models.Trailer.id == trailer_id, models.Trailer.tenant_id == tenant_id)
        .first()
    )
    if not trailer:
        return False
    db.delete(trailer)
    db.commit()
    return True


def get_trailers(db: Session, tenant_id: UUID) -> list[models.Trailer]:
    return (
        db.query(models.Trailer)
        .filter(models.Trailer.tenant_id == tenant_id)
        .order_by(models.Trailer.id.desc())
        .all()
    )

