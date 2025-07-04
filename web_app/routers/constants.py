from fastapi import APIRouter
from fastapi.responses import Response
import pandas as pd
from modules.constants import EMPLOYEE_ROLES, DRIVER_NATIONALITIES

router = APIRouter()

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
