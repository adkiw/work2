from fastapi import APIRouter
from fastapi.responses import Response
import pandas as pd
from modules.constants import EU_COUNTRIES, EMPLOYEE_ROLES, DRIVER_NATIONALITIES

router = APIRouter()

@router.get("/api/eu-countries")
def eu_countries():
    """Grąžina Europos šalių sąrašą."""
    return {"data": [{"name": name, "code": code} for name, code in EU_COUNTRIES if name]}


@router.get("/api/eu-countries.csv")
def eu_countries_csv():
    df = pd.DataFrame([
        {"name": name, "code": code}
        for name, code in EU_COUNTRIES
        if name
    ])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=eu-countries.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)

@router.get("/api/employee-roles")
def employee_roles():
    """Grąžiną darbuotojų pareigybės reikšmes."""
    return {"data": EMPLOYEE_ROLES}

@router.get("/api/employee-roles.csv")
def employee_roles_csv():
    df = pd.DataFrame(EMPLOYEE_ROLES, columns=["reiksme"])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=employee-roles.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)

@router.get("/api/driver-nationalities")
def driver_nationalities():
    """Galimų vairuotojų tautybių sąrašas."""
    return {"data": DRIVER_NATIONALITIES}

@router.get("/api/driver-nationalities.csv")
def driver_nationalities_csv():
    df = pd.DataFrame(DRIVER_NATIONALITIES, columns=["reiksme"])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=driver-nationalities.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)
