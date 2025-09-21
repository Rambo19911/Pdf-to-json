# **Juridisko PDF Dokumentu Apstrādes Sistēma (v3.0 ar GUI)**

Šis projekts ir izveidots, lai automatizēti apstrādātu juridiskos dokumentus PDF formātā. Tā mērķis ir pārveidot nestrukturētu PDF saturu tīrā, granulārā un strukturētā JSON formātā, kas ir ideāli piemērots RAG (Retrieval-Augmented Generation) sistēmām. Versija 3.0 ievieš pilnvērtīgu grafisko lietotāja saskarni (GUI), kas padara programmas lietošanu ērtu un intuitīvu.


---

## **Galvenās Iespējas (v3.0)**

* **Grafiskā Lietotāja Saskarne (GUI)**: Ērta un moderna programma, kas ļauj apstrādāt failus bez komandrindas.
* **Reāllaika Procesa Vizualizācija**: Centrālajā logā iespējams detalizēti, soli pa solim, sekot līdzi dokumenta analīzes procesam, redzot, kā skripts atpazīst pantus, punktus un apakšpunktus.
* **Elastīga Failu Atlase**: Iespēja izvēlēties apstrādei gan atsevišķu PDF failu, gan veselu mapi ar vairākiem dokumentiem.
* **Granulāra Datu Sadalīšana**: Sistēma sadala likumus pantos, punktos un apakšpunktos, nodrošinot maksimālu precizitāti.
* **Viedā Faila Pārdēvēšana**: Gala JSON fails tiek nosaukts atbilstoši dokumentā atrastajam likuma nosaukumam (piem., `Darba_likums.json`).
* **Automātiska Failu Pārvaldība**: Veiksmīgi apstrādātie PDF faili tiek automātiski pārvietoti uz `processed_pdfs` mapi, lai novērstu dubultu apstrādi.
* **Robustums un Žurnalēšana**: Kļūdainie faili tiek pārvietoti uz `error_pdfs` mapi, un viss process tiek detalizēti reģistrēts `processing.log` failā.

---

## **Projekta Struktūra**

```
.
├── input_pdfs/           # Šeit var ievietot PDF, ja izmanto veco metodi
├── processed_pdfs/       # Šeit nonāk veiksmīgi apstrādātie PDF oriģināli
├── processed_json/       # Šeit tiek saglabāti veiksmīgi apstrādātie JSON faili
├── error_pdfs/           # Šeit tiek pārvietoti PDF, kuru apstrāde neizdevās
├── gui.py                # ✅ Galvenais skripts programmas palaišanai ar UI
├── main.py               # Apstrādes loģikas vadības skripts
├── pdf_processor.py      # Modulis PDF datu ekstrakcijai un analīzei
├── validator.py          # Modulis datu validācijai
├── verify_last_file.py   # Modulis pēcapstrādes pārbaudei
├── config.py             # Konfigurācijas fails
├── requirements.txt      # Nepieciešamās bibliotēkas
└── README.md             # Šis fails
```

---

## **Uzstādīšana**

1.  **Izveidojiet Python vidi** (ja vēl nav izveidota):
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

2.  **Instalējiet nepieciešamās bibliotēkas**:
    ```bash
    pip install -r requirements.txt
    ```
    *Piezīme: Skripts pats izveidos nepieciešamās mapes (`processed_pdfs`, `processed_json`, u.c.), kad tas tiks palaists pirmo reizi.*

---

## **Lietošana**

Projekts tagad ir paredzēts darbam ar grafisko saskarni.

1.  **Palaidiet programmu**:
    ```bash
    python gui.py
    ```

2.  **Izvēlieties failus**:
    * Nospiediet pogu **"Izvēlēties PDF Failu"**, lai apstrādātu vienu dokumentu.
    * Nospiediet pogu **"Izvēlēties Mapi"**, lai automātiski apstrādātu visus PDF failus, kas atrodas izvēlētajā mapē.

3.  **Sāciet apstrādi**:
    * Nospiediet pogu **"Sākt Apstrādi"**.

4.  **Vērojiet procesu**:
    * Centrālajā logā tiks attēlota detalizēta informācija par katru apstrādes soli.
    * Progresa josla rādīs kopējo progresu, balstoties uz apstrādājamo lapu skaitu.
    * Pēc apstrādes pabeigšanas rezultātu logu varēs brīvi ritināt un pārskatīt.