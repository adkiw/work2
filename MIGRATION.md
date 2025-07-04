# FastAPI migracijos eiga

## Įgyvendinti žingsniai

1. Sukurta alternatyvi FastAPI sąsaja `web_app` kataloge.
2. Perkelti moduliai: kroviniai, vilkikai, priekabos, vairuotojai, darbuotojai, grupes, klientai, planavimas, updates ir kt.
3. Įdiegta prisijungimo ir registracijos sistema naudojant FastAPI middlewares.
4. Sukurti API maršrutai duomenų eksportui į CSV formatą.
5. Sukurta pagrindinė vartotojų administravimo funkcija (registracijų tvirtinimas ir aktyvių vartotojų sąrašas).
6. Parengti testai FastAPI versijai (`tests/` ir `fastapi_app/tests/`).
7. Pridėtas pagrindinis (`/`) maršrutas FastAPI sąsajoje.

## Numatomos užduotys

1. Toliau tobulinti šablonus, kad vaizdas atitiktų Streamlit versiją.
2. Perkelti likusius pagalbinius metodus iš `modules/utils.py`, jei jie dar naudojami.
3. Sulyginti visų formų validaciją tarp Streamlit ir FastAPI versijų.

