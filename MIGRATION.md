# FastAPI migracijos eiga

## Įgyvendinti žingsniai

1. Sukurta alternatyvi FastAPI sąsaja `web_app` kataloge.
2. Perkelti moduliai: kroviniai, vilkikai, priekabos, vairuotojai, darbuotojai, grupes, klientai, planavimas, updates ir kt.
3. Įdiegta prisijungimo ir registracijos sistema naudojant FastAPI middlewares.
4. Sukurti API maršrutai duomenų eksportui į CSV formatą.
5. Sukurta pagrindinė vartotojų administravimo funkcija (registracijų tvirtinimas ir aktyvių vartotojų sąrašas).
6. Parengti testai FastAPI versijai (`tests/` ir `fastapi_app/tests/`).
7. Pridėtas pagrindinis (`/`) maršrutas FastAPI sąsajoje.
8. Sukurtas atskiras "trailer-swap" modulis priekabų priskyrimui vilkikams.
9. "user_admin.py" funkcionalumas perkeltas į `registracijos` maršrutą.
10. Sukurtas bendras Jinja makro "header_with_add" antraštėms su "pridėti" nuoroda.
11. "header_with_add" makro pritaikytas visuose šablonuose.
12. Pridėtas stiliaus failas "style.css" ir bazinis šablonas atnaujintas jį naudoti.
13. `group_regions` lentelė papildyta `vadybininkas_id` stulpeliu atsakingam darbuotojui nurodyti.
14. Regionų priskyrimas vadybininkams perkeliamas į darbuotojo redagavimo formą.

## Numatomos užduotys

1. Toliau tobulinti šablonus, kad vaizdas atitiktų Streamlit versiją.
2. Pašalinti nebenaudojamus Streamlit modulius ir `main.py`.
3. Sulyginti visų formų validaciją tarp Streamlit ir FastAPI versijų.

## Papildomi darbai

* Patikrinti ar visos funkcijos perkeltos į `web_app` turi atitinkamus testus.

