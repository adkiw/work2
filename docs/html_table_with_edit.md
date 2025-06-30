# Paprastos lentelės su redagavimo mygtuku pavyzdys

Šiame pavyzdyje parodyta, kaip pateikti duomenų sąrašą HTML lentelėje, kurios eilučių ir stulpelių kraštinės primena „Excel“ stilių. Kiekvienos eilutės dešinėje pusėje pateikiamas koregavimo mygtukas su pieštuko ikona.

```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

<table class="excel-table">
  <tr>
    <td>Reikšmė 1</td>
    <td><button class="edit-btn"><i class="fas fa-pencil-alt"></i></button></td>
  </tr>
  <tr>
    <td>Reikšmė 2</td>
    <td><button class="edit-btn"><i class="fas fa-pencil-alt"></i></button></td>
  </tr>
</table>

<style>
  .excel-table {
    border-collapse: collapse;
    width: 100%;
  }
  .excel-table td {
    border: 1px solid #ccc;
    padding: 4px 8px;
  }
  .edit-btn {
    background: none;
    border: none;
    cursor: pointer;
  }
</style>
```

Šis kodas prideda CSS stilių, kuris tarp eilučių ir stulpelių atvaizduoja plonas linijas. Mygtukas su pieštuko ikona gali būti naudojamas redagavimo funkcijai iškviesti (reikalingas `Font Awesome` ikonų paketas).
