from sqlalchemy.orm import Session
from sqlalchemy import func
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


def create_trailer_spec(db: Session, data: schemas.TrailerSpecCreate) -> models.TrailerSpec:
    spec = models.TrailerSpec(**data.dict())
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return spec


def update_trailer_spec(db: Session, spec_id: int, data: schemas.TrailerSpecCreate) -> models.TrailerSpec | None:
    spec = db.query(models.TrailerSpec).filter(models.TrailerSpec.id == spec_id).first()
    if not spec:
        return None
    for field, value in data.dict().items():
        setattr(spec, field, value)
    db.commit()
    db.refresh(spec)
    return spec


def delete_trailer_spec(db: Session, spec_id: int) -> bool:
    spec = db.query(models.TrailerSpec).filter(models.TrailerSpec.id == spec_id).first()
    if not spec:
        return False
    db.delete(spec)
    db.commit()
    return True


def get_trailer_specs(db: Session) -> list[models.TrailerSpec]:
    return db.query(models.TrailerSpec).order_by(models.TrailerSpec.id.desc()).all()


def create_trailer_type(db: Session, data: schemas.TrailerTypeCreate) -> models.TrailerType:
    tt = models.TrailerType(name=data.name)
    db.add(tt)
    db.commit()
    db.refresh(tt)
    return tt


def update_trailer_type(db: Session, type_id: int, data: schemas.TrailerTypeCreate) -> models.TrailerType | None:
    tt = db.query(models.TrailerType).filter(models.TrailerType.id == type_id).first()
    if not tt:
        return None
    tt.name = data.name
    db.commit()
    db.refresh(tt)
    return tt


def delete_trailer_type(db: Session, type_id: int) -> bool:
    tt = db.query(models.TrailerType).filter(models.TrailerType.id == type_id).first()
    if not tt:
        return False
    db.delete(tt)
    db.commit()
    return True


def get_trailer_types(db: Session) -> list[models.TrailerType]:
    return db.query(models.TrailerType).order_by(models.TrailerType.id.desc()).all()


def set_default_trailer_types(db: Session, tenant_id: UUID, values: list[str]) -> None:
    db.query(models.DefaultTrailerType).filter(models.DefaultTrailerType.tenant_id == tenant_id).delete()
    for pr, val in enumerate(values):
        db.add(models.DefaultTrailerType(tenant_id=tenant_id, value=val, priority=pr))
    db.commit()


def get_default_trailer_types(db: Session, tenant_id: UUID) -> list[str]:
    rows = (
        db.query(models.DefaultTrailerType)
        .filter(models.DefaultTrailerType.tenant_id == tenant_id)
        .order_by(models.DefaultTrailerType.priority)
        .all()
    )
    return [r.value for r in rows]


def _compute_client_limits(db: Session, tenant_id: UUID, name: str, coface: float) -> tuple[float, float]:
    total = (
        db.query(func.sum(models.Shipment.frachtas))
        .filter(models.Shipment.tenant_id == tenant_id, models.Shipment.klientas == name)
        .scalar()
        or 0
    )
    musu = coface / 3.0 if coface else 0.0
    liks = musu - total
    if liks < 0:
        liks = 0.0
    return round(musu, 2), round(liks, 2)


def create_client(db: Session, tenant_id: UUID, data: schemas.ClientCreate) -> models.Client:
    musu, liks = _compute_client_limits(db, tenant_id, data.pavadinimas, data.coface_limitas or 0)
    client = models.Client(
        tenant_id=tenant_id,
        pavadinimas=data.pavadinimas,
        vat_numeris=data.vat_numeris,
        kontaktinis_asmuo=data.kontaktinis_asmuo,
        kontaktinis_el_pastas=data.kontaktinis_el_pastas,
        kontaktinis_tel=data.kontaktinis_tel,
        salis=data.salis,
        regionas=data.regionas,
        miestas=data.miestas,
        adresas=data.adresas,
        saskaitos_asmuo=data.saskaitos_asmuo,
        saskaitos_el_pastas=data.saskaitos_el_pastas,
        saskaitos_tel=data.saskaitos_tel,
        coface_limitas=data.coface_limitas,
        musu_limitas=musu,
        likes_limitas=liks,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def update_client(db: Session, tenant_id: UUID, client_id: int, data: schemas.ClientCreate) -> models.Client | None:
    client = (
        db.query(models.Client)
        .filter(models.Client.id == client_id, models.Client.tenant_id == tenant_id)
        .first()
    )
    if not client:
        return None
    for field, value in data.dict().items():
        setattr(client, field, value)
    musu, liks = _compute_client_limits(db, tenant_id, client.pavadinimas, data.coface_limitas or 0)
    client.musu_limitas = musu
    client.likes_limitas = liks
    db.commit()
    db.refresh(client)
    return client


def delete_client(db: Session, tenant_id: UUID, client_id: int) -> bool:
    client = (
        db.query(models.Client)
        .filter(models.Client.id == client_id, models.Client.tenant_id == tenant_id)
        .first()
    )
    if not client:
        return False
    db.delete(client)
    db.commit()
    return True


def get_clients(db: Session, tenant_id: UUID) -> list[models.Client]:
    return (
        db.query(models.Client)
        .filter(models.Client.tenant_id == tenant_id)
        .order_by(models.Client.id.desc())
        .all()
    )


def create_group(db: Session, tenant_id: UUID, data: schemas.GroupCreate) -> models.Group:
    group = models.Group(
        tenant_id=tenant_id,
        numeris=data.numeris,
        pavadinimas=data.pavadinimas,
        aprasymas=data.aprasymas,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def update_group(db: Session, tenant_id: UUID, group_id: int, data: schemas.GroupCreate) -> models.Group | None:
    group = (
        db.query(models.Group)
        .filter(models.Group.id == group_id, models.Group.tenant_id == tenant_id)
        .first()
    )
    if not group:
        return None
    for field, value in data.dict().items():
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return group


def delete_group(db: Session, tenant_id: UUID, group_id: int) -> bool:
    group = (
        db.query(models.Group)
        .filter(models.Group.id == group_id, models.Group.tenant_id == tenant_id)
        .first()
    )
    if not group:
        return False
    db.delete(group)
    db.commit()
    return True


def get_groups(db: Session, tenant_id: UUID) -> list[models.Group]:
    return (
        db.query(models.Group)
        .filter(models.Group.tenant_id == tenant_id)
        .order_by(models.Group.id.desc())
        .all()
    )

