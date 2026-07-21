# NODU KNOWLEDGE BASE
Ezt a dokumentumot a rendszer automatikusan állította elő a technikai és üzleti mappákból.
Minden részletes információt innen vegyél, ha a NODU Bridge funkcióiról, korlátairól, licenszeléséről, fejlesztési irányairól (roadmap) vagy esettanulmányairól kérdeznek.
--------------------------------------------------

## FILE: Archicad Revit Mapping 3596b1ba319a80b7a542c5edb5fd8cc0.md
Source: c:\NODU\NODU technical\Archicad Revit Mapping 3596b1ba319a80b7a542c5edb5fd8cc0.md
```
# Archicad Revit Mapping

Created by : Bendegúz Skultéty
Created time: 7 May 2026 10:05
Category: Research
Last edited by: Zoltan Poczai
Last updated time: 31 May 2026 21:05

# Archicad - Revit bridge - mapping

# Rendszerarchitektúra és Adatkonverziós Analízis: Archicad és Revit Interoperabilitás a Vizuális Szkriptelés Fényében

## Az Építményinformációs Modellezés Interoperabilitásának Ontológiai és Technológiai Kontextusa

A modern építőipari és tervezési iparágat (AEC) évtizedek óta áthatja a szoftveres fragmentáltság problémája, amelynek középpontjában a két legdominánsabb platform, a Graphisoft Archicad és az Autodesk Revit közötti adatvesztés nélküli kommunikáció áll. E két szoftver nem csupán felhasználói felületében tér el egymástól, hanem fundamentálisan eltérő adatbázis-architektúrákra, geometriai leíró nyelvekre és ontológiai elvekre épül. Míg az Archicad történelmileg egy vizuális, tervezés-orientált, objektum-alapú rendszert képvisel, amely a geometriai szabadságra és a prediktív csatlakozásokra (Priority Based Connections) helyezi a hangsúlyt , a Revit egy adat-vezérelt, relációs adatbázisokon és szigorú matematikai kényszerfeltételeken (constraints) alapuló szoftver, ahol a geometria szinte csak másodlagos leképezése a mögöttes paraméteres adathalmaznak.

A hagyományos megoldások az iparági szintű interoperabilitásra eddig a nyílt szabványokra, elsősorban az IFC (Industry Foundation Classes) formátumra támaszkodtak. Az IFC kiválóan alkalmas az Open BIM keretrendszeren belüli koordinációra, ütközésvizsgálatra (clash detection) és referenciamodellek cseréjére, ahol a cél a modellek együttes vizualizációja és ellenőrzése. Azonban a szerkeszthető, natív elemekké történő visszafejtés során az IFC formátum súlyos és áthidalhatatlan korlátokba ütközik. A transzláció során a parametrikus intelligencia elvész, a szoftverspecifikus viselkedések (például egy fal rétegrendjének vagy egy lépcső húzott fokainak algoritmikus kiszámítása) "lebutulnak" statikus határolófelület-ábrázolássá (Boundary Representation, BRep). Ebből adódóan az a mérnöki igény, hogy egy Archicadben modellezett épület natív, szerkeszthető Revit családokká (Families) és rendszerelemekké konvertálódjon, eddig nagyrészt megválaszolatlan maradt.

A fejlesztői kísérletek, amelyek a közvetlen API-szintű konverziót célozták, számos akadályba ütköztek. A "fekete doboz" (black box) jellegű konverterek, amelyek fix, a kódba égetett szabályok alapján próbáltak áthidalni két ennyire aszimmetrikus rendszert, képtelenek voltak lekezelni az építészeti gyakorlatban előforduló extrém határeseteket (edge cases). Ennek a problémának a feloldására született meg az az elképzelés, hogy a rögzített leképezési algoritmusokat egy flexibilis, a felhasználó által definiálható vizuális szkriptelő környezettel (Visual Script Engine) váltsák fel. A tervezett "Nodu" platform pontosan ezt a paradigmaváltást hozza el: a transzlációs réteget láthatóvá, paraméterezhetővé és dinamikusan módosíthatóvá teszi. Jelen jelentés mélyrehatóan elemzi az eddigi technológiai zsákutcákat – különös tekintettel a Speckle platformra –, feltárja a két szoftver belső logikai architektúráját, és egy rendkívül kimerítő, az összes létező eszközre kiterjedő leképezési mátrixot nyújt a Nodu platform fejlesztéséhez.

## A Fekete Doboz Konverterek Kudarca: A Speckle Platform Esettanulmánya

A Speckle egy innovatív, nyílt forráskódú AEC adatcsere platformként indult, amelynek deklarált célja volt az építőipari adatsilók lebontása és a különféle szoftverek közötti közvetlen geometria- és adattranszfer biztosítása. Az Archicad és Revit közötti konnektoruk ígéretes kezdeményezés volt, amely a natív elemek oda-vissza (roundtrip) konvertálására vállalkozott. A rendszer architektúrája egy C# alapú SDK-ra (speckle-sharp) épült, amely a felhasználói felületet, a szerializációt és a konverziós logikát kezelte, míg egy C++ nyelven írt Archicad AddOn felelt a Graphisoft API hívásokért és a geometria beemeléséért. Bár a Speckle sikereket ért el a metaadatok szinkronizálásában, a natív elemek teljes értékű konvertálása során kritikus technológiai hibákba futott bele, amelyek végül a platform ezen irányú ambícióinak beszűküléséhez vezettek.

Az egyik legszembetűnőbb probléma az elemek metaadatainak és funkcionális típusának elvesztése volt. A Speckle nem tudta megbízhatóan leképezni a komplex GDL objektumokat RFA (Revit Family) kategóriákra. Ennek eredményeképpen egy Archicadben precízen definiált ajtó a Revitbe érkezve gyakran értelmezhetetlen, natív tulajdonságait vesztett "Generic Model" elemként manifesztálódott. Amikor a felhasználók ugyanezt az elemet visszaküldték Archicadbe, az eredeti ajtó helyett már csak egy butított, általános "Object" érkezett meg. A konverzió ráadásul kiszámíthatatlan volt: azonos beállítások mellett is bizonyos falak falként, mások pedig felismerhetetlen geometriai testként érkeztek meg. Ez a viselkedés rávilágít a merev kódolású (hard-coded) sémák sebezhetőségére, amelyek nem képesek dinamikusan alkalmazkodni a felhasználói környezet anomáliáihoz.

A térbeli koordináció és a geometriai orientáció terén fellépő hibák tovább súlyosbították a helyzetet. A két platform teljesen eltérő módon kezeli a lokális koordinátarendszereket, a bázispontokat (Survey Point, Project Base Point) és az Északi irányt. A Speckle tesztelése során gyakori volt, hogy a Revitből származó elemek Archicadbe történő átküldése, majd érintetlen visszaküldése során az elemek rotációs torzulást szenvedtek, és elfordultak eredeti tengelyüktől. Ez az irányvektorok és a transzformációs mátrixok nem megfelelő konverziójának a tünete.

A hierarchikus és magassági kényszerek értelmezése szintén áthidalhatatlan akadálynak bizonyult. Az Archicad a falak magasságát relatív módon, az emeletekhez (Stories) köti. A Revit ezzel szemben független referenciasíkokat (Levels) használ. Amikor a Speckle behozott egy Revit falat az Archicad környezetbe, az algoritmus megpróbálta az Archicad automatikus szintkapcsolási szabályait ráerőltetni az elemre. Emiatt a fal teteje hozzárendelődött a felettes szinthez, ami gyakran a fal geometriájának drasztikus megcsonkításához és a magassági adatok torzulásához vezetett.

A komplex, sokszögesített geometriák kezelése terén a Speckle ugyancsak elvérzett. Az Archicad szabadformájú (Morph) elemeinek exportálása során a görbült felületek tesszeláción (háromszögelésen) estek át. A Revit környezetbe történő importáláskor a konverter nem volt képes megkülönböztetni a "puha" (soft) és "kemény" (hard) éleket, így az organikus formák helyett dróthálószerű, vizuálisan elfogadhatatlan poligonhalmazok jöttek létre. Végül, a hierarchikusan felépülő elemek, mint például a lépcsők és korlátok, teljes egészében hiányoztak a Speckle stabil export-import eszköztárából, mivel a C# konverziós logika nem tudta lekezelni az alárendelt al-elemek (sub-elements) rekurzív hálóját.

Ezek a tapasztalatok egyértelműen bizonyítják, hogy az automatizált, háttérben futó fekete doboz konverterek nem alkalmasak az építészeti modellek ipari szintű transzlációjára. A sikeres interoperabilitáshoz egy olyan rendszerre van szükség, ahol a felhasználó vizuálisan, csomópontonként szabályozhatja a konverziós logikát, és manuális beavatkozással kezelheti a geometriai és adatszerkezeti konfliktusokat.

## A 'Nodu' Paradigma: Vizuális Szkripteléssel Támogatott Adatleképezés

A vizuális szkriptelés a modern AEC iparág egyik legjelentősebb innovációja, amely a programozási logikát grafikus felhasználói felületre emeli, ahol csomópontok (nodes) és az azokat összekötő huzalok (wires) reprezentálják az adatfolyamot és a manipulációs lépéseket. Míg az olyan platformok, mint a Dynamo vagy a Grasshopper primeren geometriagenerálásra és algoritmikus tervezésre szolgálnak, a Nodu platform ezt az elvet az interoperabilitás és az adatszerkezeti konverzió szolgálatába állítja. A Nodu nem próbálja meg előre kitalálni a tökéletes leképezést; ehelyett egy robusztus, kiterjeszthető grafikus motor segítségével a felhasználó kezébe adja az Archicad eszközök és a Revit kategóriák közötti "mapping" (leképezés) teljes kontrollját.

Ebben a vizuális környezetben az adatfolyam a nyers metaadatok és a bázisgeometria kinyerésével kezdődik. A Nodu motorja képes kiolvasni az Archicad rejtett belső paramétereit (például a fal rétegrendjét vagy az `ac_wall_crosssection_type` változót ) és azokat bemeneti portokként megjeleníteni. A konverziós logika lelke a köztes adatmanipulációs csomópontokban rejlik. Vegyünk például egy bonyolult Archicad profilozott falat (Complex Profile). Egy hagyományos konverter ezen a ponton elakadna, és generálna egy buta térfogatot. A Nodu-ban a felhasználó felépíthet egy logikai fát: először egy feltételvizsgáló (Condition) node ellenőrzi a fal típusát. Ha a fal profilozott, a szkript egy speciális "Extract Profile" csomópontba küldi az adatot, amely a 2D kontúrt kinyerve egy Revit "In-Place Mass" vagy egy "Sweep" profillal felépített "Basic Wall" komponenst generál a túloldalon.

A vizuális szkriptelés legfőbb erénye a hibatűrés és a fallback (visszaesési) mechanizmusok kialakításának lehetősége. A szoftver fejlesztőinek nem kell minden iparági határesettel (edge case) előre tervezniük, mivel a felhasználók a Nodu felületén képesek egyedi szűrőket (Filters) és adat-kényszerítéseket (Data Coercion) beállítani. Ha egy speciális Archicad GDL gépészeti berendezés nem talál megfelelő Revit MEP Connector családot, a felhasználó létrehozhat egy dedikált mapping-node-ot, amely a GDL csatlakozási forrópontjait (hotspots) térbeli koordinátákként olvassa ki, és azok alapján automatikusan elhelyez egy generált Revit csatlakozópontot, biztosítva a rendszer logikai folytonosságát. Ez a szintű mikromenedzsment a "fekete doboz" konverterekkel fizikailag megvalósíthatatlan.

## Parametrikus Architektúrák: A GDL és a Revit Családok (Families) Ütközése

Az átjárhatóság legkomolyabb matematikai és algoritmikus akadálya a két platform parametrikus objektumkészítési filozófiájának alapvető inkompatibilitása. Az Archicad a GDL (Geometric Description Language) nevű, BASIC-szerű programozási nyelvet használja, míg a Revit a grafikus referenciákon és kötéseken (Constraints) nyugvó Family Editor rendszert alkalmazza. Ezt a fundamentális szakadékot a Nodu konverziós algoritmusaiban kristálytisztán kell kezelni.

A Revit rendszerében az elemek három szintű hierarchiába szerveződnek: Rendszercsaládok (System Families), Betölthető családok (Loadable Families) és Helyben létrehozott családok (In-Place Families). A Rendszercsaládokat (pl. falak, födémek) a szoftver belső magja vezérli, ezek nem exportálhatók vagy importálhatók egyedi RFA fájlként. A Betölthető családok vizuális szerkesztőben készülnek, ahol a geometriát referenciasíkokhoz (Reference Planes) lakatolják. A paraméterek itt szigorú típusokba soroltak (Integer, Length, Text), és formulákkal (IF, AND, OR) vezérelhetők. Kiemelendő, hogy a Revit különbséget tesz Típus (Type) és Példány (Instance) paraméterek között. Egy Típus paraméter módosítása az adott család összes példányát megváltoztatja a projektben, míg a Példány paraméter csak a kiválasztott elemet érinti.

Ezzel szemben az Archicad GDL rendszere sokkal absztraktabb és programozás-központúbb. A GDL objektumok formáját matematikai koordináták és kód-utasítások definiálják a 3D térben. Bár a Revit formulái is ismerik a feltételes utasításokat, a GDL ennél nagyságrendekkel komplexebb programozási struktúrákat – iterációs ciklusokat (FOR-NEXT), szubrutinokat, dinamikus tömböket – tesz lehetővé. Ennek leglátványosabb megnyilvánulása a paraméterfüggő felhasználói felület: egy GDL ablakban egy paraméter módosítása dinamikusan átírhatja egy másik paraméter legördülő menüjének tartalmát. Továbbá az Archicad objektumok 2D-s megjelenítése szkriptvezérelt és skálafüggő (Scale Sensitive), ami azt jelenti, hogy az elem 1:100-as és 1:20-as méretarányban teljesen más rajzolatot generálhat anélkül, hogy a 3D modell változna. A Revitben ugyanezt a 2D vonalak láthatóságának részletszinthez (Coarse, Medium, Fine) való kötésével oldják meg.

Mivel egy teljes GDL forráskód automatizált átfordítása egy relációs alapú RFA kényszer-rendszerré algoritmikusan lehetetlen feladat, a Nodu platformnak az úgynevezett "Parameter Baking" (paraméter sütés) technikát kell alkalmaznia. A konverzió pillanatában a Nodu kiértékeli a GDL objektum pillanatnyi állapotát az adott projektben, generál egy egyedi, beállított geometriát, majd az Archicad változókat (amelyeket a felhasználó kijelöl) Revit Shared vagy Project paraméterekként injektálja az újonnan kreált, vagy "In-Place" RFA elembe. Ez kompromisszum a teljes parametrikus flexibilitás és a formai hűség között, de a vizuális szkriptelő motor segítségével a felhasználó szabályozhatja ezt az adatvesztési arányt.

## Átfogó Eszköztár és Funkció Leképezési Mátrix (Exhaustive Mapping Table)

A megrendelői igényeknek megfelelően az alábbi szekciók kimerítő, teljes eszköztárra kiterjedő leképezési elemzést és adattáblákat nyújtanak. Ez a struktúra fedi le az Archicad 29 és a Revit 2026 összes létező funkcióját, lebontva azok hasonlóságait, eltéréseit és a Nodu vizuális motorja által megkívánt konverziós logikát.

### 1. Alapvető Építészeti és Térhatároló Rendszerek

Az építészeti alapfunkciók geometriailag hasonlóak, ám a belső logikájuk eltér. Az Archicad az elemek metsződését a Prioritás-alapú Építőanyagok (Building Materials) segítségével automatizálja. A szoftver kiszámítja az anyagok sűrűségét és prioritását, és automatikusan vágja a falakat és födémeket a 3D térben. Ezzel szemben a Revit egy rétegrendi hierarchiát (Core Boundary, Structure, Substrate, Finish) használ, amelyet a Join Geometry algoritmus vezérel. A Revit nem enged meg olyan szintű automatikus, globális metsződési szabadságot, mint az Archicad.

| Revit Eszköz / Kategória (BuiltInCategory) | Archicad Eszköz (Tool) | Van mindkét helyen? | Strukturális Eltérések és Konverziós Logika (Nodu) |
| --- | --- | --- | --- |
| **Basic Wall / Stacked Wall** (`OST_Walls`) | **Wall Tool** | Igen | **Eltérés:** Az AC fal lehet Simple, réteges (Composite), profilozott (Complex Profile) vagy trapéz/döntött (`ac_wall_crosssection_type`). A Revit Basic Wall csak vertikális, vagy az újabb verziókban korlátozottan dönthető (Slanted Wall). Az AC profilfalakat Revitben Sweeps/Reveals elemekkel, vagy külön in-place tömeggel lehet szimulálni.  **Nodu logika:** Réteges falak esetén a Building Material rétegeket fel kell bontani és be kell mappelni a Revit Assembly szerkesztőjének Structure/Finish zónáiba. |
| **Floor** (`OST_Floors`) | **Slab Tool** | Igen | **Eltérés:** Az AC födém sík felületű, a lejtésképzéshez tetőt vagy hálót (Mesh) használnak. A Revit Floor "Modify Sub Elements" opcióval rendelkezik, így a padló pontjai módosíthatók a drénrendszerek lejtéséhez, miközben egyes rétegek (Variable) felveszik a vastagság-különbséget.  **Nodu logika:** Az AC sík födémek 1:1 konvertálhatók. Ha Revitből küldünk változó vastagságú padlót AC-be, azt a Nodu-nak vagy egy Morph, vagy egy Roof elemmé kell degradálnia az Archicad korlátai miatt. |
| **Roof** (By Footprint, By Extrusion) (`OST_Roofs`) | **Roof Tool** (Single/Multi-plane) | Igen | **Eltérés:** Az AC összetett (Multi-plane) tető egyetlen okos elemként kezel egy teljes kontyolt tetőrendszert, vápákkal és gerincekkel. A Revit a Roof by Footprint módszerrel vonalanként (Defines Slope) generálja a síkokat.  **Nodu logika:** Az AC Multi-plane tetőt a konverzió során különálló tetősíkokká (Single-plane) érdemes bontani a pontos Revit-transzláció érdekében. |
| **Ceiling** (`OST_Ceilings`) | Nincs dedikált eszköz | Csak Revitben | **Eltérés:** Az Archicadben az álmennyezeteket a Slab (Födém) eszközzel modellezik. A Revit dedikált Ceiling kategóriája speciális gazda-felületeket (Host) biztosít a világítótestek számára, és automatikusan generál rácsozatot.  **Nodu logika:** A Nodu felhasználónak fel kell vennie egy szűrőt (Filter): Ha egy AC födém Classification-je "Ceiling", akkor azt a Revitbe `OST_Ceilings` kategóriaként kell példányosítani. |

### 2. Nyílászárók, Áttörések és Vertikális Közlekedők

A hierarchikus és gazda-elem függő (Host-based) objektumok a BIM modellek legkényesebb részei. Ahogy a Speckle esettanulmány mutatta, ezeknek az elemeknek a szétesése elkerülhetetlen, ha a konverter nem ismeri a mögöttes algoritmusokat.

| Revit Eszköz / Kategória (BuiltInCategory) | Archicad Eszköz (Tool) | Van mindkét helyen? | Strukturális Eltérések és Konverziós Logika (Nodu) |
| --- | --- | --- | --- |
| **Door / Window** (`OST_Doors`, `OST_Windows`) | **Door / Window Tool** | Igen | **Eltérés:** Az AC nyílászárók rendkívül komplex GDL objektumok, amelyek parametrikusan kalkulálják a kávát (Rebate), a küszöböt és a könyöklőt az adott fal rétegrendjéhez igazodva. A Revitben az ablakcsalád egy RFA, ahol a faláttörést (Opening Cut) külön referencia dobozok végzik.  **Nodu logika:** Közvetlen GDL-to-RFA konverzió helyett "Baking" szükséges. Az AC elem geometriáját DirectShape elemként kell átadni, de falvágó ürességgel (Void) kombinálva, hogy a Revit fal is kilyukadjon. |
| **Skylight** (Tetőablak) | **Skylight Tool** | Igen | **Eltérés:** Míg az AC-ben a tetőablak integráltan mozog a tető vagy a héj (Shell) dőlésszögével, a Revitben ez egyszerűen egy tetőre ültetett (Roof-hosted) Window család.  **Nodu logika:** A Host kapcsolatot helyre kell állítani a célmodellben, különben a tetőablak az origóba (Generic Model) konvertálódik. |
| **Stairs / Railings** (`OST_Stairs`, `OST_StairsRailing`) | **Stair / Railing Tool** | Igen | **Eltérés:** Az AC 21-ben bevezetett, majd finomított Stair Maker az ergonómiai szabályok alapján automatikusan tervezi újra a lépcső húzott fokait (Winder) és pihenőit (Landing). A Revit lépcsőkészítője merevebb, és az "uneven" (aszimmetrikus) fokokat csak rajzolt (Sketch) módban engedi meg.  **Nodu logika:** Ez volt a Speckle Achilles-sarka. A Nodu-nak le kell olvasnia az AC lépcső pontos 2D geometriai vetületét (Boundary and Riser lines), és abból kell generálnia egy vázlat-alapú (Sketch-based) Revit lépcsőt, ignorálva a Revit saját lépcső-generáló motorját. |
| **Opening** (Shaft, Wall, Face) | **Opening Tool** | Igen | **Eltérés:** Az AC dedikált Opening Tool-ja több elemen (fal, födém, tető) is áthaladhat egyszerre, és gépészeti ütközésvizsgálatból (Collision) is generálható. A Revitben külön vannak bontva: Shaft Opening (födémen át), Wall Opening és Face Opening.  **Nodu logika:** Ha az AC áttörés függőlegesen több födémet vág, a Nodu egy Revit Shaft Opening-et generál. Ha csak falat vág, akkor Wall Opening-et. |
| **Curtain Wall** (`OST_Walls` -> Curtain) | **Curtain Wall Tool** | Igen | **Eltérés:** Az AC Függönyfal moduláris rendszere (Scheme, Grid, Panel, Frame) saját mintázat-szerkesztővel bír. A Revit a függönyfalat egy fal típusnak tekinti, ahol a rácsosztás (Grid Spacing) Type paraméterként van megadva.  **Nodu logika:** Az egyedi AC osztásokat csak úgy lehet Revitbe átvinni, ha a Nodu eltávolítja a Revit Típus-kényszerét (Remove Type Association), és manuálisan, API-n keresztül generálja le az `OST_CurtainWallGrids` elemeket az AC koordináták alapján. |

### 3. Tartószerkezeti és Analitikai Modellek

Mind a Graphisoft, mind az Autodesk jelentős lépéseket tett a BIM statikai integrációja felé. Az építészeti (fizikai) modelltől elkülönülve létrejön az Analitikai Modell (SAM - Structural Analytical Model), amely végeselemes (FEM) szoftverekbe exportálható.

| Revit Eszköz / Kategória (BuiltInCategory) | Archicad Eszköz (Tool) | Van mindkét helyen? | Strukturális Eltérések és Konverziós Logika (Nodu) |
| --- | --- | --- | --- |
| **Structural Column** (`OST_StructuralColumns`) | **Column Tool** | Igen | **Eltérés:** A Revit szigorúan különválasztja a sima (Architecture) és a szerkezeti oszlopot. Az AC-ben a "Structural Function" beállítás dönti el ezt. Az AC szegmentált oszlopa (multi-segment) egy elemen belül válthat profilt.  **Nodu logika:** A Nodu a szegmentált AC oszlopot kénytelen darabolva, több egymásra helyezett Revit oszlopként leképezni, biztosítva a folytonosságot. |
| **Structural Framing** (`OST_StructuralFraming`) | **Beam Tool** | Igen | **Eltérés:** Hasonló az oszlopokhoz. Az AC gerenda ívelhető horizontálisan és vertikálisan is, és tartalmazhat lyukakat (Hole). A Revit alapértelmezetten nem támogatja a beépített gerenda-lyukakat.  **Nodu logika:** Az AC gerenda-áttöréseket Revitben `Opening By Face` elemekkel vagy egy "Void" Generic Model családdal kell utólagosan kivágni. |
| **Structural Foundation** (`OST_StructuralFoundation`) | Nincs dedikált eszköz (Slab / Morph / Wall) | Csak Revitben | **Eltérés:** Az Archicadben az alapozást vastag födémekkel (Slab), sávalapok esetén profilos falakkal (Complex Profile Wall), míg pontalapok esetén oszlopokkal vagy objektumokkal (Object) modellezik.  **Nodu logika:** Itt kulcsfontosságú a Nodu vizuális szabályrendszere. A felhasználó beállíthat egy node-ot: "Ha az AC Wall funkciója 'Foundation', akkor a konverziós kimenet legyen Revit `OST_StructuralFoundation`." |
| **Analytical Model** (Links, Nodes, Loads) | **Structural Analytical Model** | Igen | **Eltérés:** Mindkét platform képes 1D (rúd) és 2D (lemez) analitikai elemek generálására, valamint támaszok és terhek (Point, Line, Surface loads) definiálására. Az Archicad a nyílt SAF formátumot preferálja a round-trip analízishez.  **Nodu logika:** Mivel a fizikai geometria tengelye és az analitikai modell síkja eltérhet az excentricitás miatt, a Nodu-nak mindkét geometriai információt és azok kapcsolatát transzferálnia kell. |

### 4. Szabadformájú Modellezés, Terep és Burkok

A konceptuális fázis organikus geometriáinak kezelése során a pontfelhők és a BRep (Boundary Representation) konverziók dominálnak. Ez okozta a Speckle rendszerében a "tesszelációs" élhibákat.

| Revit Eszköz / Kategória (BuiltInCategory) | Archicad Eszköz (Tool) | Van mindkét helyen? | Strukturális Eltérések és Konverziós Logika (Nodu) |
| --- | --- | --- | --- |
| **Mass / In-Place Mass** (`OST_Mass`) | **Morph Tool** | Igen | **Eltérés:** Az AC Morph egy végtelenül rugalmas, teljes értékű BIM felület/test modellalkotó (Push/Pull, Smooth edges). A Revit "Conceptual Massing" egy elkülönített modellezési tér, amiből a végén felület-alapú (Face-based) épületelemeket lehet húzni.  **Nodu logika:** Az AC Morph poligonjait DirectShape kategóriába kell konvertálni Revitben. A Nodu vizuális szűrőivel meg kell határozni a látható (hard) és rejtett (soft) éleket, elkerülve a roncsolódott drótháló effektust. |
| Nincs dedikált eszköz (Massing) | **Shell Tool** | Csak AC-ben | **Eltérés:** Az AC Shell (Héj) szabályozott, kettős görbületű réteges felületeket generál (Kihúzott, Forgatott, Szabályozott). A Revitben ezt csak Mass felületen elhelyezett tetővel (Roof by Face) lehet replikálni.  **Nodu logika:** A Shell geometriáját átmenetileg egy Revit Mass elemmé kell fordítani a háttérben, majd rá kell feszíteni egy tető rétegrendet. |
| **Toposolid** (`OST_Topography`) | **Mesh Tool** | Igen | **Eltérés:** Az AC Mesh pontokat és éleket összekötő poligonfelület, aminek vastagsága van. A Revit sokáig csupán vékony felületként kezelte (Toposurface), de a Revit 2024/2026-os verziókban bevezetett Toposolid egy réteges, szilárdtest-modell, amely már vágható (Excavation) és padlószerűen módosítható.  **Nodu logika:** A Revit új Toposolid fejlesztése óriási könnyebbség. Az AC Mesh topológiai pontjait (Z-koordinátáit) egy az egyben le lehet képezni a Revit Toposolid alpontjaira, megőrizve a terep rétegrendjét és vastagságát. |

### 5. Épületgépészeti (MEP) Rendszerek és Hálózatok

A Revit történelmileg egy multidiszciplináris szoftver integrált MEP motorral. A Graphisoft az Archicad 29-ben integrálta a korábban kiegészítőként futó MEP Modeler-t, így megjelent a natív MEP Designer. A gépészet Achilles-sarka a nyomvonalak folytonossága és a logikai rendszerek.

| Revit Eszköz / Kategória (BuiltInCategory) | Archicad Eszköz (MEP Designer) | Van mindkét helyen? | Strukturális Eltérések és Konverziós Logika (Nodu) |
| --- | --- | --- | --- |
| **Duct / Duct Fitting** (`OST_DuctCurves`) | **Ductwork / Routing** | Igen | **Eltérés:** Az AC rugalmas, folytonos kattintásokkal vezérelt nyomvonalat (Routing) épít, a töréspontokon automatikus idomokkal. A Revit zárt, matematikai "Logical System"-ben gondolkodik (pl. Elszívott levegő, Friss levegő), ahol minden idom pontos RFA család.  **Nodu logika:** A csövek geometriai konverziója nem elég. A Nodu-nak újra kell alkotnia a Revit logikai hálózatát: fel kell fűznie a darabokat egy létrehozott MEP System-re, különben a Revitben a hidraulikai számítások nem fognak működni. |
| **Pipe / Pipe Fitting** (`OST_PipeCurves`) | **Pipework / Routing** | Igen | **Eltérés:** Az Archicad 29 nagy előrelépése a lejtett csövek (Sloped pipes) intuitív módosíthatósága. A Revitben a gravitációs (lejtett) csőrendszerek módosítása híresen nehézkes, és gyakran a rendszer széteséséhez vezet.  **Nodu logika:** A Nodu számára kihívás a lejtésszögek konverziója: az AC csövek induló (Start) és érkező (End) magassági adatait kell a Revit csövek "Invert Elevation" beállításaiba injektálni. |
| **Cable Tray / Conduit** (`OST_CableTray`) | **Cabling** | Igen | **Eltérés:** Geometriailag hasonló routing rendszer, de a Revit kiterjedt áramköri (Circuit) adatbázissal rendelkezik az elektromos rendszerekhez. |
| **Mechanical Equipment** / Plumbing Fixtures | **Equipment / Accessory** | Igen | **Eltérés:** Az AC MEP berendezések (kazánok, hőcserélők) paraméteres GDL elemek integrált csatlakozási "hotspot"-okkal. A Revitben az áramlási irányt, a besorolást és a csatlakozó méretét speciális "MEP Connector" intelligens entitások definiálják az RFA családon belül.  **Nodu logika:** A konverzió során az Archicad csatlakozási forrópontjaiból a Nodu-nak Revit MEP Connector elemeket kell generálnia a megfelelő paraméterekkel, hogy a csőhálózat rácsatlakozhasson. |

### 6. Terep, Zónák és Logikai Csoportosítások

A terek menedzselése nem geometriai, hanem információs feladat. A modell elemzése ezen adatokon nyugszik.

| Revit Eszköz / Kategória (BuiltInCategory) | Archicad Eszköz (Tool) | Van mindkét helyen? | Strukturális Eltérések és Konverziós Logika (Nodu) |
| --- | --- | --- | --- |
| **Room / Space** (`OST_Rooms`, `OST_Spaces`) | **Zone Tool** | Igen | **Eltérés:** A Revit szétválasztja az építészeti helyiséget (Room) és a gépészeti zónát (Space), amelyek a környező határoló elemeket érzékelik 2D-ben és kiterjesztik 3D-ben. Az AC Zóna Tool ezzel szemben egy 3D térfogati test, amely automatikusan levágja magát a ferde tetőknél és pontos kubatúrát számol.  **Nodu logika:** Mivel a Revit helyiségek a Level-ekhez (Szintek) kötöttek, az AC térbeli zónáit a konverter a Level bounding box-okra kénytelen leképezni. Ha a pontos 3D AC térfogati reprezentációra van szükség, a zónákat statikus Mass elemként kell exportálni. |
| **Area** (`OST_Areas`) | **Fill Tool** (Területszámítás) | Részben | A Revit kiterjedt területrendezési és színezési rendszerekkel (Area Plan) bír. Az Archicadben ezt nagyrészt a Zónák és a 2D Kitöltések (Fills) biztosítják. |
| **Group / Assembly / Model Group** | **Group / Hotlinked Module** | Igen | **Eltérés:** A Revit Model Group-ok lehetővé teszik ismétlődő egységek együttes kezelését. Az Archicad ezt külső hivatkozású Modulokkal (Hotlinked Modules) vagy belső Csoportosítással oldja meg.  **Nodu logika:** A Modulok konverziója során a Nodu vizuális felületén eldönthető, hogy a modul tartalmát felrobbantva (explode) elemeire bontsa a célmodellben, vagy beágyazott Revit "Link" fájlként próbálja megérteni. |

### 7. 2D Dokumentáció, Feliratok és Nézetek

A konverterek – köztük a Speckle – gyakran elkövetik azt a hibát, hogy kizárólag a 3D modellre koncentrálnak. Egy igazi építészeti irodában a 2D dokumentáció elvesztése kritikus. A Nodu platformnak a 2D elemeket is le kell tudnia képezni.

| Revit Eszköz / Kategória (BuiltInCategory) | Archicad Eszköz (Tool) | Van mindkét helyen? | Strukturális Eltérések és Konverziós Logika (Nodu) |
| --- | --- | --- | --- |
| **Section / Elevation / Callout** | **Section / Elevation / Detail / Worksheet** | Igen | **Eltérés:** Mindkét programban generatív nézetekről van szó, amelyek élőben frissülnek. A Revitben a Callout (Kiemelés) egy detail view-t hoz létre, az AC-ben a Detail Tool független vonalakká bontja a modellt.  **Nodu logika:** A metszeti vonalak koordinátáinak és látószögeinek transzferálása kritikus. A Nodu képes legenerálni a Revit nézeteket (Views) az Archicad markerek pozíciója alapján. |
| **Dimension** (`OST_Dimensions`) | **Dimension Tool** | Igen | **Eltérés:** A Revit méretezései ideiglenes (Temporary) dimenziókként is funkcionálnak, amelyek a kényszereket hajtják, míg az AC méretezései asszociatív módon kötődnek az elemek pontjaihoz.  **Nodu logika:** A felrajzolt 2D méretezési láncokat a Nodu-nak az elemek referenciapontjaihoz (References) kell kötni a Revit API-ban, különben egyszerű vonalakká esnek szét. |
| **Text / Tag** (`OST_TextNotes`, `OST_Tags`) | **Text / Label Tool** | Igen | **Eltérés:** A Revit feliratai (Tags) kategória-specifikusak (pl. Door Tag, Window Tag), és paraméteres mezőket olvasnak ki. Az AC Címke (Label) eszköz univerzálisan rámutathat bármelyik elem bármely paraméterére (Properties).  **Nodu logika:** A Nodu-ban fel kell építeni egy "Tag Generator" gráfot, amely az AC Label tartalmát kiértékeli, és létrehoz egy statikus szöveget (TextNote), vagy ha paraméterről van szó, generál egy megfelelő Revit Tag-et. |
| **Detail Component / Filled Region** | **Line, Fill, Circle, Polyline** | Igen | Alapvető szerkesztési eszközök. A Revit Filled Regionje a Draft view-kra korlátozott, míg az AC Fill Tool szabadon használható a térben is. |

## A Magassági Kényszerek és a Térbeli Hierarchia (Story vs. Level) Feloldása

Amint az a Speckle esettanulmányból kiderült, a térbeli adatszerkezet a BIM egyik legkritikusabb Achilles-sarka. Az Archicad hierarchiája szigorúan emeletekre (Stories) tagozódik. A szoftver elvárja, hogy minden elemhez tartozzon egy "Home Story" (Kiaduló szint). Ennek folyományaként a falak teteje asszociatívan rögzíthető a felettes szinthez (Story + 1), így a szintek magasságának módosításakor a geometria dinamikusan követi azt. Ezzel szemben a Revit egy sokkal lazább, matematikai referenciasík-rendszert használ (Levels). A Revitben tetszőleges számú szint generálható egy projektben, és ezek csupán virtuális vízszintes síkokként funkcionálnak. Gyakori, hogy egy építész külön Level-t hoz létre a parapetmagasságnak, az álmennyezetnek és a födém alsó síkjának.

Amikor a Nodu Archicad modellt konvertál Revitbe, az algoritmus az AC Story-kat gond nélkül le tudja képezni alap Revit Level-ekké, beállítva a megfelelő bázis- és csúcskényszereket (Base/Top Constraints) az épületelemekre. A probléma fordított irányban gyökerezik: egy komplex Revit projekt 50-60 Level-lel történő Archicadbe importálása katasztrófát okoz. Az Archicad minden egyes Revit Level-t külön Emeletként próbálna értelmezni, ami teljesen szétverné a 2D alaprajzi struktúrát, a felirati rendszereket és a metszeti logikát.

Itt válik felbecsülhetetlenné a Nodu vizuális szkriptelő motorjának rugalmassága. A felhasználó egy egyszerű adatmanipulációs gráf (Node Graph) segítségével definiálhatja a szűrési szabályokat: *„Csak azokat a Revit Level-eket fordítsd Archicad Story-ra, amelyek nevében szerepel a 'Floor' vagy 'FFL' (Finished Floor Level) kifejezés. Az összes többi segéd-Level esetében (pl. Parapet Level) az ahhoz kötött elemeket számítsd át lokális elem-offszetre, és kösd azokat a legközelebbi fő szinthez.”* Ez a fajta adat-transzformációs logika az, amely kiküszöböli a "fekete doboz" konverterek végzetes hibáit, és emberi intelligenciával ruházza fel az algoritmikus konverziót.

## Fejlesztési Irányelvek a Konverziós Algoritmusok Optimalizálásához

A Nodu platform fejlesztése megköveteli a platformspecifikus illúziók elhagyását: sosem fog létezni olyan gomb, amely matematikai tökéletességgel egy az egyben átemel egy parametrikus épületet két eltérő ontológiájú szoftver között. Az interoperabilitás sikere a testreszabhatóságban és a tudatos adatvesztési protokollok menedzselésében rejlik.

A platform jövőbeli sikeréhez a következő architekturális irányelveket kell a Nodu vizuális motorjába építeni:

1. **Dinamikus Szótárak (Mapping Dictionaries) Elkülönítése:** Ne az alap kód (C++) próbálja meg kitalálni az elemek közötti statikus kapcsolatot. A Nodu vizuális motorja tegye lehetővé a felhasználóknak, hogy elmentsenek és megosszanak saját "Leképezési Csomagokat". Egy belsőépítész iroda számára egy függönyfal szétrobbantott 3D vonalakként való importálása tökéletesen megfelelhet, míg egy homlokzattervező mérnök ragaszkodni fog a natív `OST_CurtainWallGrids` struktúrához.
2. **Kettős Geometriai Transzfer (BRep és Parametrikus egyidejűleg):** A csomópontoknak (Nodes) meg kell engedniük a kettős adatfolyamot. Amikor az algoritmus egy GDL objektumot konvertál RFA fájllá, a GDL elem eredeti, tökéletes BRep "kagylóját" (Shell) is le kell menteni egy rejtett al-rétegként, mint fallback opció, ha a parametrikus rekonstrukció a Revitben meghiúsulna vagy topológiai torzulást szenvedne.
3. **Paraméteres Kényszer-sütés (Constraint Baking):** Az Archicad beépített viselkedési szabályait (pl. a GDL változók ciklusait és a Priority Based Connections hatásait) a konverzió pillanatában le kell fagyasztani, azaz "meg kell sütni". A Revitnek nem az Archicad kódját kell megkapnia, hanem a kód lefutása utáni, statikus fizikai állapot eredményét, amelyet azután statikus Shared Paraméterekként és manuálisan szerkesztett Instance paraméterekként lehet tovább vinni.
4. **Koordináta Transzformációs Bázispontok (Origin Nodes):** A Speckle elcsúszási hibáiból okulva , a Nodu vizuális hálójának első és kötelező eleme kell legyen a Helyi Koordinátarendszer, a Project Base Point és a Survey Point explicit összehangolása, ahol a transzformációs mátrixok (eltolás, forgatás, skálázás) transzparens módon, a felhasználó által felülírható módon működnek.

Összegezve, az Archicad és Revit közötti átjárhatóság nem tisztán szoftveres, hanem kognitív probléma. A Nodu a vizuális szkripteléssel áthidalja ezt a szakadékot, megadva az adatmérnököknek azt a szabadságot, hogy maguk írják meg a saját projektjükre szabott, aszimmetrikus BIM konverziós szabályrendszerüket, ezzel végleg maga mögött hagyva az előző generációs megoldások merev és sérülékeny architektúráját.
```

--------------------------------------------------

## FILE: nodu-research-v2.md
Source: c:\NODU\NODU technical\nodu-research-v2.md
```
# NODU – Piaci Research v2
*2026-04-24 | Forrás: Bendegúz sales playbook · AEC BIM 2.0 (Martyn Day) · Esser et al. (2023) TU München · Data-Driven Construction (Boiko, 2025) · KFI pályázat (FDB-Dijkstra) · Neszmélyi L. (BME 2015)*

---

## 0. Egy mondatban

A nodu egy **gráf-alapú operációs platform**, amely a tervezés, gyártmánytervezés, gyártás és pénzügyi kontroll között fennálló adatvesztési spirált szünteti meg — egyetlen összefüggő adatmodellen, amit senki más nem csinál.

**Bizonyított számok (németországi homlokzatburkolat projekt, ~2500 m²):**
- 800 h → 150 h gyártmánytervezés | **−83%**
- 2000 elemből 5 újragyártás | **0,25% hibaarány**
- 15% anyagmegtakarítás | SEW-Graben referencia, 2D stock cutting + neurális háló

---

## 1. A piaci probléma — az információs szakadék

### Miért vérzik el a hagyományos kivitelezés?

Az adatvesztés nem egy pillanati esemény. Egy folyamat — és minden átadásnál visszairreverzibilisen romlik.

```
Archicad / Revit
    ↓  [IFC export — parametrikus logika elvész]
Gyártmánytervező (Excel + PDF)
    ↓  [manuális újraértelmezés, verziókáosz]
CNC / gyártósor
    ↓  [fájlküldés e-mailben, nincs visszacsatolás]
Helyszín (papír rajzok, WhatsApp)
    ↓  [nincs visszacsatolás a tervbe]
Pénzügyi kontroll (utólag, ha egyáltalán)
```

Minden nyíl: potenciális adatvesztés, manuális újraértelmezés, hibaforrás.

### A 4 fő fájdalom

**1. Újratervezési spirál.** Egyetlen tervmódosítás az egész lánc újrafuttatását igényli — geometria, rögzítési logika, anyaglista, gyártás-előkészítés. A döntés és a megvalósítás között hetek telnek el.

**2. Láthatatlan pénzügyi következmények.** Vezetői szinten nem látszik, mekkora margin-vesztést okoz egy tervváltoztatás. A kár utólag derül ki.

**3. Logisztikai és helyszíni káosz.** Ha egy elem hiányzik a helyszínen, a tervezett szerelési sorrend felborul. Improvizáció, utólagos drága korrekció.

**4. Garanciális vak folt.** A change-orderek e-mailekben és Excel-táblákban tűnnek el. Évekkel később lehetetlen rekonstruálni, hogy tervezési, gyártási vagy szerelési hiba volt-e.

### Amit a piac valójában kér

A Data-Driven Construction (Boiko, 2025) és a piaci elemzések ugyanarra mutatnak: az építőipar az egyik **utolsó iparág**, amely adatvezérelt döntéshozatalra áll át. A KPMG 2023-as felmérése szerint az építőipari vállalatok vezetői a **PMIS, az advanced analytics és a BIM kombinációjától** várják a legnagyobb ROI-t. Az akadály nem a technológia — hanem az adatsilók és a strukturálatlan folyamatok.

> „A vezető szoftverfejlesztők nem lesznek a változás motorjai az építőiparban — sokuk számára az adatvezérelt megközelítés veszélyt jelent a bevett üzleti modelljükre." — Boiko, 2025

---

## 2. A technológiai mag — miért más a nodu

### 2.1 Building Information Graph (BIG)

A nodu nem fájlokban gondolkodik. **Gráfban.**

Az építőipari projekt egy összefüggő gráf:
- **Csomópontok** = elemek (panel, csavar, munkafázis, kifizetés, alvállalkozó)
- **Élek** = logikai kapcsolatok (fal ↔ rá kerülő panel, tervváltozás ↔ pénzügyi hatás)

Ha a gráf egyik pontja megváltozik, a hatás automatikusan propagálódik minden érintett elemhez. Ez a BIG-keretrendszer biztosítja, hogy az adatok ne fájlként, hanem **működő projektlogikaként** éljenek tovább — export és újraértelmezés nélkül.

**Akadémiai validáció:** Az Esser et al. (2023, TU München, Automation in Construction) paper formálisan bizonyítja, hogy a BIM-modellek gráfként reprezentálva — objektum-szintű diff-patch-merge mechanizmussal — objektum-szintű változáskövetést és automatikus konfliktusfeloldást tesznek lehetővé. Ez pontosan az, amit a nodu delta-alapú adatcseréje valósít meg: nem 5 GB-os modelleket mozgatunk, csak a tényleges változásokat és hatásaikat.

### 2.2 Visual Script Engine (VSE) — a rendszer agya

A parametrikus logika a VSE-ben él, nem a fájlban.

- A Computational Designer és az Építész ugyanazon a modellen dolgozik, scriptjeik és kompetenciáik ütközése nélkül
- Archicad parametrikus fájl → VSE változói → Revit: a logikai kapcsolatok sérülés nélkül mennek át
- Agentic Workflow: természetes nyelven, chat-alapon irányítható a generatív folyamat — mély szoftveres ismeret nélkül

Példa: *„Módosítsd a panelek kiosztását 600×1200-as raszterre, igazítsd a nyílászárókhoz"* → a rendszer újraszámolja az egész panelkiosztást és vágási tervet.

### 2.3 Dijkstra motor — az optimalizáló

A Dijkstra-algoritmus (Edsger W. Dijkstra, 1956) az irányított gráfok legrövidebb útját keresi. A nodu constraint optimizer alapja:

- Homlokzati panelkiosztás optimalizálása anyaghozatal és statika szerint, a generálás során
- Wave Function Collapse (WFC) rasztergenerálás
- 2D stock cutting + neurális háló: anyaghulladék minimalizálása (15% igazolva a SEW-Graben projekten)
- Graph grammar alapú tervezési szabályok kódolása

A brand neve ebből ered: Dijkstra = „legrövidebb út a homlokzat tervezéstől a kivitelezésig".

### 2.4 Geometry as code

A BIM 2.0 cikk (Martyn Day, AEC Magazine) leírja a következő paradigmaváltást: az épületek nem fájlokból épülnek fel, hanem **végrehajtható leírásokból** (geometry as code). A tervező szándékot deklarál — korlátokat, célokat — a rendszer kiszámolja a geometriát.

A nodu VSE-je pontosan ezt csinálja. A jelenlegi BIM-eszközök (Revit, Archicad) procedurálisan és elem-objektum-centrikusan tárolják az adatot — a szándék a tervező fejében van, nem a szoftverben. **Ez az, ami meggátolja, hogy az MI-ágensek érdemben érjék el és értsék a modellt.**

### 2.5 Összefoglalás: technológiai stack

| Komponens | Technológia |
|---|---|
| 3D motor | C++ + WebAssembly (böngészőben, asztali teljesítménnyel) |
| Adatmodell | BIG — Building Information Graph |
| Constraint solver | Dijkstra + GA + WFC + graph grammar |
| AI / agentic | LLM multiágens, chat-alapú vezérlés |
| Anyagoptimalizálás | 2D stock cutting + neurális háló |
| Verziókövetés | Delta-alapú, objektum-szintű (nem fájl-szintű) |
| Integráció | API + MCP szerverek (Archicad, Revit, ERP, CRM) |

---

## 3. Piaci kontextus — hová megy a BIM?

### 3.1 A BIM 2.0 forduló (Martyn Day)

Jelenleg 6+ startup verseng az asztali, fájlalapú BIM-eszközök (Revit, Archicad) ellen — Snaptrude, Qonic, Arcol, Hypar, Forma, NeoBIM. Jobbak a Revitnél, de ugyanolyan alapfeltevéssel dolgoznak: a tervező előbb megalkotja a geometriát, a mérnök utólag ellenőrzi.

**Az igazi forduló már zajlik a mérnöki diszciplínákban:**
- **Augmenta:** egyetlen éjszaka alatt 25 mérföldnyi elektromos nyomvonal generálása egy adatközpont-tervhez
- **Branch 3D:** tartószerkezeti váz, amely valós időben újraszámolja magát a geometria változásával

A mérnöki diszciplínák billenőponton vannak az **„egylépéses megoldhatóság"** (one-pass solvability) felé. Az építészet még nem — de a közte és a mérnöki automatizáció között növekvő aszimmetria átírja a teljes fázisalapú tervezési folyamatot (RIBA fázisok, tervbefagyasztások).

**A következtetés (Day):** *„Egy megoldó-vezérelt környezetben a mérnöki munka nem utólagos ellenőrzés — magában a tervezés aktusában foglal helyet."*

### 3.2 Miért halnak meg a jelenlegi BIM-eszközök

**Revit (25 éves befagyasztott mag):** fájlalapú, elem-objektum-centrikus. A szándék a tervező fejében van. A gráf szintjén nincs intelligencia. Az Autodesk megoldása (Forma, APS tokenizált API): meglévő felhasználókat kell magával vinnie → lassú migráció.

**Speckle:** adatokat mozgat szoftverek között, de nem tartja meg a parametrikus logikát. Az átküldésnél az összefüggések elvesznek. Az Esser et al. paper is megjegyzi: a Speckle peer-to-peer relay megközelítése „new data exchange standard kockázatát hordozza" és nem kezeli az objektum-szintű változáskövetést.

**BIM 2.0 startupok (Snaptrude, Hypar, Arcol stb.):** jobb kollaboráció, felhőalapú — de nem gráf-natívak. Modellezők, nem operációs platform.

### 3.3 Az adat-vezérelt építés hiánya (Boiko, 2025)

A Data-Driven Construction könyv central tézise: az építőipar az egyetlen nagy iparág, ahol a döntéshozatal még mindig elsősorban a **HiPPO-elven** működik (Highest Paid Person's Opinion — a legjobban fizetett ember véleménye dönt, nem az adat). Ez közvetlen összefüggésben van a projekt-margin-vesztéssel.

Boiko meghatározza az „adatsilók" fogalmát: különálló szoftvereszközök — CAD, ERP, CRM, raktárkezelő, pénzügyi szoftver — amelyek nem kommunikálnak egymással. Minden eszközváltás adatvesztéssel jár.

**A nodu megoldása:** umbrella platform, ahol ezek az eszközök API-n vagy MCP szervereken keresztül kapcsolódnak egy közös gráf-adatmodellbe — és az adatvesztés megszűnik.

### 3.4 Ütemezés és pénzügyi szinkron (Neszmélyi, BME 2015)

Az építési ütemtervek (CPM/PERT hálós ütemterv, Gantt, szalagos ütemterv lineáris projekteknél) a Neszmélyi-féle BME-anyag szerint egy alapvető problémával küzdenek: **az ütemterv és a pénzügyi valóság szétcsúszik**, amint az építés megkezdődik.

> „Az ütemterv azért készül, hogy tudjuk, mitől térünk el." — Neszmélyi L.

A nodu ERP-szinkronja és Model ID-alapú haladáskövetése pontosan ezt a rést zárja be: az ütemtervi és a pénzügyi valóság egyetlen adatmodellen fut, valós időben.

---

## 4. Modulok és készültségi szint (2026 Q2)

### Core platform

| Modul | Állapot | Funkció |
|---|---|---|
| **VSE (Visual Script Engine)** | ✅ 100% | Parametrikus logika, geometry as code |
| **ERP Hub** | ✅ 100% | Pénzügy, task, óra, projekt struktúra |
| **BIM–Gyártás–Kivitelezés szinkron** | ✅ 100% | Model ID alapú nyomonkövetés, gyártótól helyszínig |
| **3D Model Viewer** | ✅ 100% | Böngészős megjelenítés, táblanézet, property kezelés |
| **Archicad Connector** | ✅ 100% | Séma + modell feltöltés, delta sync |
| **Rhino 3dm / Grasshopper** | ✅ 100% | Szubgráf input |

### Domain modulok

| Modul | Állapot | Funkció |
|---|---|---|
| **Homlokzat Generátor** | 🔄 70% | 2D rajzból 3D burkolat + háttérszerkezet, CNC export |
| **Procurement** | 🔄 90% | Beszállítói lánc, készletoptimalizálás |
| **Manufacturing workflow** (n8n) | 🔄 50% | Gyártási folyamat orchestration |
| **Approval flow** | 🔄 80% | Design → jóváhagyás → gyártás pipeline |
| **AI / Agentic Workflow** | 🔄 50% | Chat-alapú vezérlés, szövegből modell generálás |
| **Automata ütemtervező** | 🧪 POC | Múltbeli adatokon alapuló prediktív erőforrásbecslés |

### Kritikus hiányosságok (licenszblokkoló)

1. **Manufacturing workflow** — ha az ügyfél gyárt, ez blokkoló
2. **Cost code struktúra** — a pénzügyi szinkron csak ezzel teljes
3. **Multitenancy / workspace invite** — enterprise sales előfeltétel

---

## 5. Kompetitor landscape

| Termék | Kategória | Gráf-natív? | Ahol a nodu jobb |
|---|---|---|---|
| **Revit** | Legacy BIM | ❌ Fájlalapú, befagyasztott mag | Gráf-motor, ERP szinkron, optimizer |
| **Autodesk Forma** | BIM 2.0 kísérlet | ❌ Tokenizált API | Nyílt architektúra, nincs per-touch díj |
| **Snaptrude / Arcol** | BIM 2.0 modellező | ❌ | BIG + gyártás + pénzügyi szinkron |
| **Hypar** | Generatív BIM | ⚠️ Geometry as code (részben) | Integrált ERP, manufacturing, constraint solver |
| **Speckle** | Adat-relay | ⚠️ Relay, nem gráf | Parametrikus logika megőrzése (Esser et al. validálja a különbséget) |
| **Procore** | Construction OS | ❌ Project management | Parametrikus design + constraint solver |
| **Bentley iTwin** | Digital twin | ⚠️ Adat-platform | Constraint solver, manufacturing integráció |

### A nodu 5 egyedi tulajdonsága

1. **Gráf-natív** — nem fájlalapú BIM-re épül, hanem BIG-re
2. **Parametrikus kontinuitás** — logika megmarad az átadásokon (Esser et al. validálja ezt mint a piac hiányosságát)
3. **Constraint-based optimizer** — Dijkstra, GA, WFC, graph grammar, 2D stock cutting
4. **Manufacturing + ERP szinkron** — egyetlen rendszeren belül, amit a BIM 2.0 startupok nem csinálnak
5. **Geometry as code** — a tervező szándékot deklarál, a motor kiszámolja a geometriát (Day: ez a következő paradigma)

---

## 6. ROI és esettanulmányok

### Németországi alumínium homlokzatburkolat (~2500 m²)

| Metrika | Előtte | Nodával | Változás |
|---|---|---|---|
| Gyártmánytervezési idő | 800 óra | 150 óra | **−83%** |
| Gyártási hibaarány | ismeretlen | 5 / 2000 elem | **0,25%** |
| HQ láthatóság | napi e-mail | valós idejű, Model ID | **teljes** |

### SEW-Graben projekt

**15% anyagmegtakarítás** — 2D stock cutting + neurális háló optimalizáción. Nem marketing, hanem kemény számok.

### Mit jelent ez EUR-ban?

Egy 800→150 h különbség ~650 mérnöki óra. Ha a mérnöki óra 40 EUR: **26 000 EUR megtakarítás egyetlen projekten** — a platformdíjon felül. A 15% anyagmegtakarítás homlokzatburkolaton jellemzően szintén több tízezer EUR.

---

## 7. ICP és sales implikáció

### Ideális vevő

**Firmográfia:**
- Design-build cég — nem csak tervez, gyárt és kivitelez is
- 20–200 fő, vagy nagyobb cég fókuszált divíziója
- Homlokzat, prefab, acélszerkezet, útépítés szegmens
- Párhuzamosan 3–5+ futó projekt
- Van belső technológiai döntéshozó

**Trigger jelek:**
- Aktívan keres Archicad–Revit interoperabilitási megoldást
- Panaszkodik gyártmánytervezési torlódásra
- Elveszített margint kezel tervváltozások miatt
- BIM mandátumra készül (EU közbeszerzés, ESG követelmény)
- Külföldi projektre terjeszkedik, ahol HQ koordináció a szűk keresztmetszet

**Negatív ICP:**
- Csak tervező iroda (nincs gyártás/kivitelezés → ERP szinkron értéke minimális)
- Mikrovállalkozás (< 10 fő)
- Csak lakóépületes generálkivitelező

### Sales narratíva

**10 mp:** „A nodu az egyetlen platform, amely a tervtől a pénzügyi zárásig egyetlen gráfban tartja a projektet — parametrikus logika vesztése nélkül."

**2 perc:** „Design-build cégeknél az adatvesztés az IFC exportoknál kezdődik és soha nem áll meg. Gyártmánytervezési selejt, helyszíni káosz, utólagos margin-vesztés. A nodu gráf-alapú motor ezt szünteti meg: a geometria, az anyagjegyzék, az ütemterv és a pénzügyi kontroll egyetlen élő adatmodellben él. Referenciánkon: 800 mérnöki óra lett 150, 2000 elemből 5 hibás."

### Hármas buyer persona

| Szerep | Fájdalom | Mit akar | Kifogás |
|---|---|---|---|
| **Champion** (senior PM / tech lead) | Napi koordinációs káosz | Automatizált folyamat | „Nem tudom, hogyan vezessük be" |
| **Economic Buyer** (CEO / CFO) | Margin-vesztés, garanciális kockázat | ROI, auditálhatóság | „Mennyi ideig tart a megtérülés?" |
| **Technical Evaluator** (BIM lead / IT) | Integráció, adatbiztonság | API, on-premise opció | „Illeszkedik a meglévő stackhez?" |

---

## 8. Roadmap és stratégia

### Szegmentált belépési prioritás

| Szegmens | Tech readiness | Referencia | Gyártás integráció |
|---|---|---|---|
| **Facade / homlokzat** | ✅ Kész | ✅ FDB / Dijkstra | ✅ CKV workflow fut |
| **Prefab / acélszerkezet** | ⚠️ Részben | ❌ | ⚠️ Manufacturing 50% |
| **Infra (út, vasút)** | ⚠️ Motor kész | ❌ | ⚠️ Tervezési fázis |
| **MEP / gépészet** | ❌ Nincs domain UI | ❌ | ❌ |

### Bővítési logika

```
2026: Homlokzat → pilot zárás, Dijkstra brand IP
2027: Nyílászárók, függönyfalak → VSE bővítés
2027: Vonalas építés (útépítés) → infra domain plugin
2028: Betonozás, zsaluzat → teljes horizontális platform
```

### Földrajzi stratégia (KFI alapján)

**1. Magyarország (most)** — legszigorúbb szabályozás → ha itt működik, mindenhol működik. Pilotok, referenciák.

**2. USA (2027–2028)** — homogén piac, egy szabályozás, nagy területen sok felhasználó. Egyszeri piac-specifikus testreszabás.

**3. Ázsia + EU (2029+)** — US tapasztalatokkal és referenciákkal.

---

## 9. Nyitott kérdések (prioritás szerint)

### Sales-blokkoló
- [ ] Pilot pricing: ingyenes? kedvezményes? success fee?
- [ ] Mi a minimális belépő csomag (land)? Mi az upsell path (expand)?
- [ ] On-premise deploy opció: mikor lesz kész? (enterprise blocker)
- [ ] Manufacturing workflow: konkrét UX ha az ügyfélnek saját gyártósora van?

### Piac-méretezés (hiányzik)
- [ ] Design-build cégek száma: Magyarország / CEE / DACH?
- [ ] Átlagos software spend egy design-build cégnél évente?
- [ ] Procore / Autodesk Forma konkrét árazása?

### Technológiai
- [ ] Van más gráf-natív BIG-kompatibilis piaci szereplő?
- [ ] Speckle pontos objektum-szintű változáskövetési képessége?
- [ ] Text2BIM (Du et al.) vs. nodu AI modul: objektív benchmark?

---

## Appendix: Dokumentum-katalógus

| # | Dokumentum | Típus | Kulcs-tartalom |
|---|---|---|---|
| 1 | **Bendegúz sales playbook** | Belső | Termékleírás, modulok, ROI adatok, kompetitor elemzés, narratíva |
| 2 | **KFI pályázat (FDB-Dijkstra)** | Belső | Brand eredet, tech stack (WFC/graph grammar/DL/RL), csapat, stratégia |
| 3 | **AEC BIM 2.0** (Martyn Day) | Piaci | Agent-based BIM jövő, execution runtime, geometry as code, engineering automation |
| 4 | **Esser et al. (2023)** — TU München | Akadémiai | Gráf-alapú BIM verziókezelés, diff-patch-merge, Speckle-kritika, BASE elvek |
| 5 | **Data-Driven Construction** (Boiko, 2025) | Szakkönyv | Adatsilók, HiPPO-döntéshozatal, ERP/PMIS integráció, AI/LLM az építőiparban |
| 6 | **Neszmélyi L. (BME, 2015)** | Szakkönyv | CPM/PERT, Gantt, szalagos ütemterv, erőforrás-tervezés, pénzügyi szinkron igénye |

---

*Élő dokumentum. Frissítsd minden pilottal, minden komolyabb prospect interakcióval és minden sprint után, ahol a termékállapot változik.*
```

--------------------------------------------------

## FILE: Nodupluginsystem.txt
Source: c:\NODU\NODU technical\Nodupluginsystem.txt
```
# Figjam

[https://www.figma.com/board/D3q9sTpH3PJW48SYGVneEs/Plug-In-System-🔌?node-id=0-1&t=78SEc1DAdXNsyI4S-1](https://www.figma.com/board/D3q9sTpH3PJW48SYGVneEs/Plug-In-System-%F0%9F%94%8C?node-id=0-1&t=78SEc1DAdXNsyI4S-1)

# Figma

[https://www.figma.com/board/D3q9sTpH3PJW48SYGVneEs/Plug-In-System-🔌?node-id=0-1&t=LNdyD0EknekUbUlE-1](https://www.figma.com/board/D3q9sTpH3PJW48SYGVneEs/Plug-In-System-%F0%9F%94%8C?node-id=0-1&t=LNdyD0EknekUbUlE-1)

[Roles and Permissions](https://www.notion.so/Roles-and-Permissions-1746b1ba319a8048a252c1a17b4ed54b?pvs=21) 

# 🔍 Research

## Atlassian

It is important to distinguish between Atlassian Data Center and Atlassian Cloud.

- Data Center is the self-hosted version, managed on the client’s own server
- In the other hand Atlassian Cloud is hosted by Atlassian in their own infrastructure

### What plugins are there?

Mostly, Jira and Confluence plugins are available on the marketplace. Most of them are automations, reports, or time tracking functions.
It is also possible to create and publish self-developed plugins

### Hosting location

There is no actual hosting. The plugins are integrated from a dedicated plugins folder

- Data Center: self-hosted
- Atlassian Cloud: Atlassian’s marketplace

### System integration

- UI: With configuration files. The developer can specify where the element should be displayed
    - Atlassian SDK examples:
        - system.header/left
        - system.header/right
        - atl.jira.view.issue.left.context
        - atl.jira.view.issue.right.context
        - …
    - Atlassian Forge examples:
        - jira:issuePanel
        - jira:adminPage
        - jira:projectPage
        - …
- Backend:
    - Atlassian SDK: With event listeners. The developer can specify on which event should the function run. Examples:
        - IssueUpdatedEvent
        - GroupUpdatedEvent
        - IssueCommentedEvent
        - …
    - Atlassian Forge: Similar to the Atlassian SDK, the developer can define event listeners with the same event names. Alternatively, automation rules can be used too. Automation rule examples:
        - jira:workflowCondition
        - jira:workflowValidator
        - jira:workflowPostFunction
        - …

### Can the plugin add custom data to Jira issues?

Jira allows users to create custom fields in its interface, and a plugin can call this function too. The plugin can also add a custom fields to the issue table directly, but this method is not recommended by the Atlassian development team, because it might conflict with other plugins when modifying the same table.

Instead, the recommended solution for plugins to manage their own separate tables.

### How can the plugin data queried?

If the plugin inserts a column directly into the issue table or creates a custom field using Jira's built-in function, the data becomes automatically searchable with JQL. However, if the plugin modifies the database table, the applicable search operations must be defined for it. (e.g., “=”, “~”, “in”)

In other cases, if the plugin uses its own table, the developer must define the interface, the operators, and index the data (e.g., using Lucene) to make it searchable

### Can the plugin use another plugin's data?

Yes, plugin “A” can access data from plugin “B”. For this functionality, plugin “B” has to export the data, plugin “A” has to import it, and plugin “A” has to mark plugin “B” as a dependency.

### What programming languages can be used?

- Data Center: Java
- Atlassian Cloud: JavaScript (TypeScript recommended)

### Permissions

The plugin configuration file has to define what Atlassian permissions the plugin wants to access

Atlassian permission scope examples:

- User
- Work
- Project
- …

Plugin permission request examples:

- read:jira-user
- write:jira-work
- manage:jira-project
- …

During a user session, the user permissions can be listed and checked before a specific function call. Alternatively, the plugin can check if the user has permission for a specific action (e.g., hasCreatePermission).

In case if the plugin wants to manage custom permissions, it has to create and manage its own permissions table.

### Billing system

There are three different option

- Paid via Atlassian: The customer purchases the plugin via Atlassian
- Paid via Vendor: The customer purchase it from external website
- Free

### Other informations

- The plugin communicates with the Atlassian server through REST API calls
- Plugins are usually developed for specific applications like Jira or Confluence, but system-level plugins can also be created through Shared Access Layer (SAL)
- The Atlassian system uses Webpack for module bundling and loading

### Links

[Atlassian Developer](https://developer.atlassian.com/)

[Forge Examples](https://developer.atlassian.com/platform/forge/example-apps-jira/)

[Permission Scopes](https://developer.atlassian.com/cloud/jira/platform/scopes-for-oauth-2-3LO-and-forge-apps/)

[Plugin Billing](https://developer.atlassian.com/platform/marketplace/pricing-payment-and-billing/)

[Shared Access Layer](https://developer.atlassian.com/server/framework/atlassian-sdk/about-sal-development/)

## Linear

Communication between Linear integrations and Linear's servers is only possible via APIs and Webhooks.

### What plugins are there?

Mostly integrations with larger applications.

### Hosting location

The plugin has to be submitted to Linear via Google Form and it is expected to be hosted on their servers.

### System integration

-

### Can the plugin add custom data to the Linear tables?

No, it can only use the existing ones via GraphQL.

### How can the plugin data queried?

-

### Can the plugin use another plugin's data?

Probably not.

### What programming languages can be used?

JavaScript and TypeScript

### Permissions

The permissions of the authenticated user are being used. Technically, the user is interacting with the Linear through the API.

### Billing system

-

## Clickup

## Figma

# 🤖 Talk with Copilot

## Marketplace-based software solutions

Marketplace-based software solutions are **platforms** that allow third-party developers to build and distribute apps, plugins, or modules that extend the core functionality of the software. These ecosystems foster collaboration, customization, and scalability. Here are several well-known examples across different domains:

---

### **1. Productivity & Collaboration**

- **Atlassian Marketplace**: Offers apps for Jira, Confluence, Bitbucket, etc. Popular for project management, agile development, and documentation.
- **Figma Community**: Designers can share plugins, widgets, and UI kits to extend Figma’s collaborative design capabilities.
- **Slack App Directory**: Hosts integrations and bots that enhance Slack’s communication platform.

---

### **2. Business Management & ERP**

- **Odoo Apps**: A modular ERP system with thousands of apps for CRM, accounting, inventory, HR, and more.
- **Salesforce AppExchange**: A massive marketplace for CRM-related apps, automation tools, and industry-specific solutions.
- **Zoho Marketplace**: Offers extensions for Zoho’s suite of business tools (CRM, Books, Projects, etc.).

---

### **3. E-commerce**

- **Shopify App Store**: Apps for marketing, shipping, inventory, and customer service to enhance online stores.
- **Magento Marketplace (Adobe Commerce)**: Extensions for payment, SEO, analytics, and more.
- **BigCommerce App Marketplace**: Integrations for store management, marketing, and logistics.

---

### **4. Development Platforms**

- **Visual Studio Marketplace**: Extensions for VS Code and Visual Studio, including themes, debuggers, and language support.
- **JetBrains Marketplace**: Plugins for IntelliJ IDEA and other JetBrains IDEs.
- **GitHub Marketplace**: Tools for CI/CD, code quality, security, and project management.

---

### **5. Cloud & Infrastructure**

- **AWS Marketplace**: Pre-configured software, machine learning models, and infrastructure tools.
- **Azure Marketplace**: Solutions for cloud computing, AI, databases, and more.
- **Google Cloud Marketplace**: Offers container images, VMs, and SaaS apps.

## Focusing on the Productivity & Collaboration and the **Business Management & ERP categories**

| **Platform** | **Core Focus** | **Marketplace Name** | **Features for Developers** | **Pricing Model for Apps** | **Notable Strengths** |
| --- | --- | --- | --- | --- | --- |
| **Atlassian** | Project management, DevOps | Atlassian Marketplace | REST APIs, Forge/Connect frameworks, SDKs | Free, Paid (monthly/yearly) | Deep Jira/Confluence integration |
| **Figma** | UI/UX design collaboration | Figma Community | Plugin API (JavaScript), Widget API | Free to publish, mostly free | Real-time design collaboration |
| **Odoo** | ERP & business management | Odoo Apps | Python-based modules, XML views, Odoo Studio | Free, Paid (one-time or subs) | Modular ERP, open-source flexibility |
| **Salesforce** | CRM & customer engagement | AppExchange | Apex, Lightning Web Components, APIs | Free, Paid (subscription) | Enterprise-grade CRM, robust ecosystem |
| **Zoho** | Business suite (CRM, HR, etc.) | Zoho Marketplace | Deluge scripting, REST APIs, Zoho Creator | Free, Paid | Integrated suite, low-code tools |

## **Workflow for Creating & Publishing Third-Party Tools**

### **1. Atlassian Marketplace**

- **Participants**: Developer, Atlassian (review team), End-users
- **Workflow**:
    1. **Develop**: Use Atlassian Forge or Connect to build apps using REST APIs.
    2. **Test**: Locally or in Atlassian’s dev environment.
    3. **Submit**: Upload to the Atlassian Marketplace.
    4. **Review**: Atlassian performs **security and compliance** checks.
    5. **Publish**: Once approved, the app is listed.
    6. **Maintain**: Developers can push updates and respond to user feedback.
- **UX Tips**:
    - Provide clear documentation and onboarding.
    - Use Forge for better integration and performance.
    - Monitor analytics and reviews to iterate quickly.

---

### **2. Figma Community**

- **Participants**: Developer/Designer, Figma (light moderation), End-users
- **Workflow**:
    1. **Develop**: Use Figma Plugin API (JavaScript/HTML/CSS).
    2. **Test**: Inside Figma’s plugin environment.
    3. **Submit**: Publish via the Figma Community portal.
    4. **Review**: Light moderation for content and functionality.
    5. **Publish**: Instantly available to users.
- **UX Tips**:
    - Focus on simplicity and speed.
    - Include animated previews and usage examples.
    - Engage with users via comments and updates.

---

### **3. Odoo Apps**

- **Participants**: Developer, Odoo (optional review), End-users
- **Workflow**:
    1. **Develop**: Build modules in Python with XML for UI.
    2. **Test**: Locally or in Odoo.sh.
    3. **Submit**: Upload to the Odoo App Store.
    4. **Review**: Optional; some apps are auto-published.
    5. **Publish**: Available for download or purchase.
- **UX Tips**:
    - Offer demo data and screenshots.
    - Ensure compatibility with Odoo versions.
    - Use Odoo Studio for low-code enhancements.

---

### **4. Salesforce AppExchange**

- **Participants**: Developer, Salesforce Security Review Team, End-users
- **Workflow**:
    1. **Develop**: Use Apex, LWC, and Salesforce APIs.
    2. **Test**: In Salesforce Developer Edition.
    3. **Submit**: Package and submit via AppExchange Partner Portal.
    4. **Review**: Mandatory security review (can take weeks).
    5. **Publish**: After approval, app is listed.
- **UX Tips**:
    - Invest in passing the security review early.
    - Provide guided setup flows and Trailhead modules.
    - Use Lightning Design System for native UX.

---

### **5. Zoho Marketplace**

- **Participants**: Developer, Zoho Review Team, End-users
- **Workflow**:
    1. **Develop**: Use Deluge or Zoho Creator.
    2. **Test**: In sandbox or Creator environment.
    3. **Submit**: Through Zoho Marketplace portal.
    4. **Review**: Zoho checks for functionality and compliance.
    5. **Publish**: App becomes available to Zoho users.
- **UX Tips**:
    - Use Zoho’s low-code tools for rapid prototyping.
    - Include detailed user guides and videos.
    - Offer customization options for different industries.

# **Payment systems**

Here’s a breakdown of how **payment systems** work for developers and end-users across the five marketplace-based platforms:

---

## **Payment & Billing Models by Platform**

| **Platform** | **Who Pays?** | **How Payment Flows** | **Billing Entity for End-User** | **Developer Payouts** | **Notes** |
| --- | --- | --- | --- | --- | --- |
| **Atlassian Marketplace** | End-user (via Atlassian) | Through Atlassian Marketplace | **Atlassian** issues invoices | Developers are paid by Atlassian monthly (minus fees) | Atlassian handles taxes, renewals, and refunds **1** |
| **Figma Community** | Mostly free (some paid) | Direct or via Stripe (for paid plugins) | **Developer** (if using Stripe) | Direct via Stripe (if monetized) | Monetization is limited and still evolving |
| **Odoo Apps** | End-user (via Odoo App Store) | Through Odoo (if listed on store) or direct (if self-hosted) | **Odoo** (if purchased via store) | Developers receive payouts from Odoo | Developers can also sell independently |
| **Salesforce AppExchange** | End-user (via Salesforce) | Through Salesforce billing system | **Salesforce** | Developers receive revenue share from Salesforce | Requires partnership and security review |
| **Zoho Marketplace** | End-user (via Zoho) | Through Zoho Marketplace | **Zoho** | Developers receive payouts from Zoho | Revenue share model; Zoho handles billing |

## **Key DetailsEnd-User Billing**

- **Atlassian, Salesforce, Zoho**: Users receive invoices from the platform itself.
- **Figma**: If monetized, billing is handled via Stripe by the developer.
- **Odoo**: Depends on whether the app is sold through the official store or independently.

### **Developer Revenue**

- **Atlassian**: Developers receive monthly payouts after Atlassian deducts a commission (typically 25%).
- **Salesforce**: Revenue share model; Salesforce handles all billing and payouts.
- **Zoho**: Similar to Salesforce, with a revenue share and payout system.
- **Figma**: Developers can monetize via Stripe (if enabled).
- **Odoo**: Developers can choose to sell via Odoo’s store or independently.

# **Add-on configuration and permission management**

Here’s how **add-on configuration and permission management** typically works across the five platforms:

---

## **⚙️ Add-On Settings & Permissions by Platform**

### **1. Atlassian Marketplace (Jira, Confluence, etc.)**

- **Settings Location**: Managed via the **Universal Plugin Manager (UPM)**.
    - Navigate to **Settings > Apps > Manage Apps**.
    - Each installed app may have a **“Configure”** button that opens its settings panel.
- **Permissions**:
    - Admins control which users can install or configure apps.
    - Some apps allow **role-based access control** within their own settings.
- **UX Note**: Settings are centralized in the UPM, but each app may have its own UI for deeper configuration  .

---

### **2. Figma Community**

- **Settings Location**:
    - Plugins are accessed via the **right-click menu** or **Resources panel**.
    - Settings are usually built into the plugin UI itself (e.g., modal or sidebar).
- **Permissions**:
    - Admins can approve plugins for **specific workspaces or the entire organization**.
    - No granular role-based permissions per plugin, but workspace-level control exists .
        
        **3**
        
- **UX Note**: Lightweight and plugin-specific; no central settings dashboard.

---

### **3. Odoo Apps**

- **Settings Location**:
    - Each module integrates into the Odoo backend and may add its own **menu items or settings tab**.
    - Configuration is often found under **Settings > Apps** or within the module’s own section.
- **Permissions**:
    - Odoo has a robust **role and access rights system**.
    - You can define **user groups** and assign permissions per module or even per field.
- **UX Note**: Highly integrated; settings are context-sensitive and follow Odoo’s modular structure.

---

### **4. Salesforce AppExchange**

- **Settings Location**:
    - Installed apps appear in **App Launcher** or **Setup > Installed Packages**.
    - Each app may include its own **custom settings page** or **Lightning components**.
- **Permissions**:
    - Uses Salesforce’s **Profiles and Permission Sets**.
    - Admins can control access to apps, objects, fields, and components.
- **UX Note**: Centralized control via Setup, but apps often have their own configuration UIs.

---

### **5. Zoho Marketplace**

- **Settings Location**:
    - Apps are managed via **Zoho Marketplace > Installed Extensions**.
    - Each extension may have a **“Settings”** or **“Configure”** option.
- **Permissions**:
    - Controlled via **Zoho Admin Panel**.
    - Role-based access can be defined per app or module.
- **UX Note**: Centralized for admins, but app-specific for users.
```

--------------------------------------------------

## FILE: Sprint planning 2c46b1ba319a80f095f1c8702878690f.md
Source: c:\NODU\NODU technical\Sprint planning 2c46b1ba319a80f095f1c8702878690f.md
```
# Sprint planning

Category: Planning
Created by: József L. Kiss
Date: 9 December 2025

# Sprint goals

### 🎄🎄🎄 Az optimizer kiszámolja a legjobb raster felosztást 🎄🎄🎄

BIM:

- Legyen alkalmas az új VSE engine Archicadből érkező reference elem fogadására, GraphQL-en keresztül, Postmanből lehessen elérni ezeket a funkciókat
    - Visual Script Engine 2.0:
        - A jelenlegi kód külön repo(k)ba kerül❌
        - Elkészül autoteszt legalább 6 test esetre❌
        - Regressziót biztosító CI automata teszt❌
    - Visual Script Service:
        - Endpoint készüljön el, ami a VSE interfészét adja❌
- Visual Script UI:
    - beleintegrálódik a facademodeler pluginba a UI szinten (design inputok listája, kártyák kinézete, connection-ök, slotok kinézete legyen lekövetve)❌

AI / Optimizer:

- Az optimalizáció lefut raszterre
    - rasterizerhez készül egy constraint solver plugin, amely generative designnak megfelelően felosztja a falat❌
    - meglévő panel optimizer genetikus algoritmus át lesz írva plugin-osra❌
    - panel optmizer kiszámolja a cost függvényt❌
    - (nice-to-have: rasterháló realtime vizualizációja)❌

ERP:

- Bugfixes
- ERP refactor
    - Permission rendszer elkészül backend✅
    - Permission rendszer elkészül frontend❌
    - Dynamically register plugins frontend❌
    - GraphQL query-k egymásba integrálása elkészül❌
- CKV
    - Ajtó/ablak ajánlatadás már a Dijkstrán tud menni (https://linear.app/dijkstrasolution/issue/DIJ-925/implement-ckv-workflow-for-glassdoor-business)✅

DevOps:

- Preview release does not work with platform plugin in dev (frontend part) https://linear.app/dijkstrasolution/issue/DIJ-952/preview-release-does-not-work-with-platform-plugin-in-dev-frontend❌

Design:

- Door/Window CKV - UX/UI Design review collab with Hunor❌[https://linear.app/dijkstrasolution/issue/DIJ-890/design-ideation-doorwindow-ckv-in-n8ndirectus](https://linear.app/dijkstrasolution/issue/DIJ-890/design-ideation-doorwindow-ckv-in-n8ndirectus)
- “Public” roadmap - Add a road map to the Release notes page in [Notion](https://www.notion.so/Nodu-Development-2b66b1ba319a80d299afec9288cfa9f8?pvs=21) [https://linear.app/dijkstrasolution/issue/DIJ-940/public-roadmap-add-a-road-map-to-the-release-notes-page-in-notion](https://linear.app/dijkstrasolution/issue/DIJ-940/public-roadmap-add-a-road-map-to-the-release-notes-page-in-notion)❌
- Spike - Navigation in 3D model environment [https://linear.app/dijkstrasolution/issue/DIJ-941/spike-navigation-in-3d-model-environment](https://linear.app/dijkstrasolution/issue/DIJ-941/spike-navigation-in-3d-model-environment)✅
- Design for Dijkstra mails [https://linear.app/dijkstrasolution/issue/DIJ-889/design-for-dijkstra-email](https://linear.app/dijkstrasolution/issue/DIJ-889/design-for-dijkstra-email)❌

Release notes:
```

--------------------------------------------------

## FILE: Sprint planning 2ee6b1ba319a80dbb0e1f3f5c071da5c.md
Source: c:\NODU\NODU technical\Sprint planning 2ee6b1ba319a80dbb0e1f3f5c071da5c.md
```
# Sprint planning

Created by: József L. Kiss
Date: 20 January 2026

# Sprint goals

🔴 - Nem lesz meg

🟡 - Meglehet de még nincs kész / Review-ban van

🟢 - Megvan (élesben!)

---

### BIM: Model feltöltése Archicadből, status állítás lehetőséggel

- Legyen alkalmas az új VSE engine Archicadből érkező reference elem fogadására, API-n keresztül, Postmanből lehessen elérni ezeket a funkciókat
    - Visual Script Engine 2.0:
        - Regressziót biztosító CI automata teszt 🔴
        - Array, enum típusok bevezetése 🟢
    - Visual Script Service:
        - Endpoint készüljön el, ami a VSE interfészét adja 🔴
        - Package-ként legyen hostolva 🔴
        - Hibakezelés legyen megoldott 🔴
- Archicad Connector
    - Le tudja definiálni a sémát (reference elem (mesh) + property szinten) 🔴
    - Fel tudja populálni a modellt 🔴
    - Eldől, hogy CEF vagy natív **C++** 🟢
- Model Viewer
    - Mesh-ek megjelenítése az új modellből 🔴
    - Status-ok/ütemek kezelése elkészül 🔴
        - UI-ok meglesznek
        - Schema bővítése (status-ok + slot-ok elem szinten)
        - Szelekció alapon lehessen statust/ütemet állítani elem szinten

### AI / Optimizer: Wave function collapse test + Waste calculator with GA Main

- Wave function collapse kipróblása 🟢
    - https://linear.app/dijkstrasolution/issue/DIJ-1044/wave-function-collapse-raster-generation
- NON-PRIO → Replace waste calculator with main genetic algorithm 🔴
    - https://linear.app/dijkstrasolution/issue/DIJ-1053/replace-waste-calculator-with-main-genetic-algorithm
- Plan VSE + optimizer integration 🔴
- Review: 🟢
    - Az optimalizáció lefut raszterre
        - rasterizerhez készül egy constraint solver plugin, amely generative designnak megfelelően felosztja a falat
        - meglévő panel optimizer genetikus algoritmus át lesz írva plugin-osra
        - panel optimizer kiszámolja a cost függvényt

### **ERP: Dinamikus plugin regisztráció elkészül**

- Project fogalom bevezetésre kerül 🔴
    - https://linear.app/dijkstrasolution/issue/DIJ-1020/introduce-project-concept-on-hub-level
- User groups elkészül backend szinten 🟢
- Review:
    - Elfelejtett jelszó funkció elkészül 🟢
    - ERP refactor 🔴
        - Permission rendszer elkészül frontend
        - Dynamically register plugins frontend
- CKV
    - TBD! @József L. Kiss
    - + hibajavítások:
        - https://linear.app/dijkstrasolution/issue/DIJ-1041/design-bugs-in-the-new-ckv-flow 🔴
        - https://linear.app/dijkstrasolution/issue/DIJ-996/hub-clears-url-search-params-on-back-navigation 🔴
- Manufacturing
    - Tervezés szinten előáll a gyártástámogatás munkafolyamata 🔴
- Todo
    - Vibe codinggal készüljön el a todo rendszer kezdeti állapota (https://linear.app/dijkstrasolution/issue/DIJ-1043/implmenet-task-management-with-vibecoding) 🟢

DevOps:

- Timlogs: 🔴
    - https://linear.app/dijkstrasolution/issue/DIJ-659/update-logged-times-from-clockify-to-dijkstra
    - [https://linear.app/dijkstrasolution/issue/DIJ-1000/service-monitor-rendszer](https://linear.app/dijkstrasolution/issue/DIJ-1000/service-monitor-rendszer)Clockify-Clockify sync: https://linear.app/dijkstrasolution/issue/DIJ-946/clokify-to-clokify-sync
- https://linear.app/dijkstrasolution/issue/DIJ-1015/docker-image-registry 🔴
- https://linear.app/dijkstrasolution/issue/DIJ-1033/add-clockify-reports-to-daily-standup-meeting-memo 🔴
- [https://linear.app/dijkstrasolution/issue/DIJ-1000/service-monitor-rendszer](https://linear.app/dijkstrasolution/issue/DIJ-1000/service-monitor-rendszer) 🔴

Design:

- **ERP**
    - **Projects** [https://linear.app/dijkstrasolution/issue/DIJ-1028/project-design](https://linear.app/dijkstrasolution/issue/DIJ-1028/project-design) 🔴
    - **Settings (Manangement/Admin)** [https://linear.app/dijkstrasolution/issue/DIJ-1028/project-design](https://linear.app/dijkstrasolution/issue/DIJ-1028/project-design) 🔴
- **Model viewer - Remaining features** [https://linear.app/dijkstrasolution/issue/DIJ-1052/model-viewer-design-for-the-remaining-features](https://linear.app/dijkstrasolution/issue/DIJ-1052/model-viewer-design-for-the-remaining-features) 🔴
- **Marketing & PR strategy** - Ongoing [https://linear.app/dijkstrasolution/issue/DIJ-1007/planning-dijkstra-strategy-q1](https://linear.app/dijkstrasolution/issue/DIJ-1007/planning-dijkstra-strategy-q1) 🔴

Roadmap:

- “Public” roadmap - Add a road map to the Release notes page in [Notion](https://www.notion.so/Nodu-Development-2b66b1ba319a80d299afec9288cfa9f8?pvs=21) [https://linear.app/dijkstrasolution/issue/DIJ-940/public-roadmap-add-a-road-map-to-the-release-notes-page-in-notion](https://linear.app/dijkstrasolution/issue/DIJ-940/public-roadmap-add-a-road-map-to-the-release-notes-page-in-notion) 🟢
```

--------------------------------------------------

## FILE: Sprint planning 2fd6b1ba319a80f39532fcbd45fd2155.md
Source: c:\NODU\NODU technical\Sprint planning 2fd6b1ba319a80f39532fcbd45fd2155.md
```
# Sprint planning

Category: Planning
Created by: József L. Kiss
Date: 4 February 2026

# Sprint goals

---

### BIM: Model feltöltése Archicadből, status állítás lehetőséggel elkészül

- Legyen alkalmas az új VSE engine Archicadből érkező reference elem fogadására, API-n keresztül, Postmanből lehessen elérni ezeket a funkciókat
    - Visual Script Engine 2.0:
        - Regressziót biztosító CI automata teszt 🟢
    - Visual Script Service:
        - Endpoint készüljön el, ami a VSE interfészét adja 🟢
        - Package-ként legyen hostolva 🔴
        - Hibakezelés legyen megoldott 🟢
- Archicad Connector
    - Le tudja definiálni a sémát (reference elem (mesh) + property szinten) 🟢
    - Fel tudja populálni a modellt 🟢
- Model Viewer
    - Mesh-ek megjelenítése az új modellből 🟢
    - Status-ok/ütemek kezelése elkészül 🟢
        - UI-ok meglesznek
        - Schema bővítése (status-ok + slot-ok elem szinten)
        - Szelekció alapon lehessen statust/ütemet állítani elem szinten

### **BIM: Rhino file format support elkészül**🔴

- Rhino 3dm file import az új VSE-t használja
- Fileból egy használható modell készül

### AI / Optimizer: Wave function collapse test + Waste calculator with GA Main

- Wave function collapse kipróblása 🟢
    - https://linear.app/dijkstrasolution/issue/DIJ-1044/wave-function-collapse-raster-generation
- NON-PRIO → Replace waste calculator with main genetic algorithm 🔴
    - https://linear.app/dijkstrasolution/issue/DIJ-1053/replace-waste-calculator-with-main-genetic-algorithm
- Plan VSE + optimizer integration 🔴
- Review: 🟢
    - Az optimalizáció lefut raszterre
        - rasterizerhez készül egy constraint solver plugin, amely generative designnak megfelelően felosztja a falat
        - meglévő panel optimizer genetikus algoritmus át lesz írva plugin-osra
        - panel optimizer kiszámolja a cost függvényt

### **ERP: Dinamikus plugin regisztráció és project fogalom elkészül**

- Dinamikus plugin regisztráció 🟢
    - Required/nem required plugin-ok kezelhetőek lesznek (Dijkstra.Models ilyen legyen)
- Project fogalom bevezetésre kerül 🟢
    - https://linear.app/dijkstrasolution/issue/DIJ-1020/introduce-project-concept-on-hub-level
- GraphQL egymásba ágyazhatóság elkészül 🟢
    - https://linear.app/dijkstrasolution/issue/DIJ-948/graphql-implements
- CKV
    - TBD! @József L. Kiss
    - + hibajavítások:
        - https://linear.app/dijkstrasolution/issue/DIJ-1041/design-bugs-in-the-new-ckv-flow 🔴
        - https://linear.app/dijkstrasolution/issue/DIJ-996/hub-clears-url-search-params-on-back-navigation 🔴
- Manufacturing
    - Tervezés szinten előáll a gyártástámogatás munkafolyamata 🔴
- Todo
    - Vibe codinggal készüljön el a todo rendszer kezdeti állapota (https://linear.app/dijkstrasolution/issue/DIJ-1043/implmenet-task-management-with-vibecoding) 🟢

DevOps:

- Timlogs: 🔴
    - https://linear.app/dijkstrasolution/issue/DIJ-659/update-logged-times-from-clockify-to-dijkstra 🔴 (Tamáson van)
    - Monitoring: [https://linear.app/dijkstrasolution/issue/DIJ-1000/service-monitor-rendszer](https://linear.app/dijkstrasolution/issue/DIJ-1000/service-monitor-rendszer) 🟢
    - Clockify-Clockify sync: https://linear.app/dijkstrasolution/issue/DIJ-946/clokify-to-clokify-sync 🟢
- Docker Images: https://linear.app/dijkstrasolution/issue/DIJ-1015/docker-image-registry 🟢
- https://linear.app/dijkstrasolution/issue/DIJ-1033/add-clockify-reports-to-daily-standup-meeting-memo 🔴

Design:

- **ERP**
    - **Projects** [https://linear.app/dijkstrasolution/issue/DIJ-1028/project-design](https://linear.app/dijkstrasolution/issue/DIJ-1028/project-design) 🟢
    - **Settings (Manangement/Admin)** [https://linear.app/dijkstrasolution/issue/DIJ-1028/project-design](https://linear.app/dijkstrasolution/issue/DIJ-1028/project-design) 🟢
- **Model viewer - Remaining features** [https://linear.app/dijkstrasolution/issue/DIJ-1052/model-viewer-design-for-the-remaining-features](https://linear.app/dijkstrasolution/issue/DIJ-1052/model-viewer-design-for-the-remaining-features) 🟢
- **Marketing & PR strategy** - Ongoing [https://linear.app/dijkstrasolution/issue/DIJ-1007/planning-dijkstra-strategy-q1](https://linear.app/dijkstrasolution/issue/DIJ-1007/planning-dijkstra-strategy-q1) 🟢

Roadmap:

- “Public” roadmap - Add a road map to the Release notes page in [Notion](https://www.notion.so/Nodu-Development-2b66b1ba319a80d299afec9288cfa9f8?pvs=21) [https://linear.app/dijkstrasolution/issue/DIJ-940/public-roadmap-add-a-road-map-to-the-release-notes-page-in-notion](https://linear.app/dijkstrasolution/issue/DIJ-940/public-roadmap-add-a-road-map-to-the-release-notes-page-in-notion) 🟢
```

--------------------------------------------------

## FILE: Sprint planning 30a6b1ba319a808897d3ea5aa021db4f.md
Source: c:\NODU\NODU technical\Sprint planning 30a6b1ba319a808897d3ea5aa021db4f.md
```
# Sprint planning

Category: Planning
Created by: József L. Kiss
Date: 17 February 2026

# Sprint goals

---

### BIM: Table view for elements

- Ability to store and retrieve history information of VSE connection @Giron Gergő 🔴
- API improvements @Giron Gergő
    - REST API kitakarítás 🔴
    - Visual Scripting Service: bináris file-ok kezelése Nexusban, CI folyamat 🟢
    - DijkstraPlatform beolvasztása a BIM.ModelServer repoba 🔴
    - Authentication támogatása 🔴
- UI @Norbert Hajdu
    - Alap táblázati nézet elkészül az elemekkel 🟢
    - Filterezés, keresés, szelektálás/izoláció modellben 🟢
    - OOS: history kezelés alapszinten elkészül 🔴

### **BIM: Rhino file format support elkészül @Adrián**

- Rhino 3dm file import az új VSE-t használja🟢
- Fileból egy használható modell készül🟢
- Támogatja a modell update-et🟢
- Az elemek azonosítói nem meshként exportálódnak, hanem adatként🟢
- Az elemek azonosítói vizualizálni lehet a viewerben🔴

### **BIM: File attachments @Bence Nemes**

- Hub-level API which supports Cloudflare storage 🔴
- …

### AI / Optimizer: Wave function collapse test + Waste calculator with GA Main

- NON-PRIO → Replace waste calculator with main genetic algorithm 🔴
    - https://linear.app/dijkstrasolution/issue/DIJ-1053/replace-waste-calculator-with-main-genetic-algorithm
- Plan VSE + optimizer integration 🟢

### **ERP: Settings oldal elkezdése**

- HUB
    - Sentry, A hiba logolásra, de dsn hiányzik 🔴
    - Localization, mindent amit lehet fordítsuk le magyarra, és a nyelv választó részt készítsük el 🔴
    - Settings UI:
        - User Groups UI elkészül mock adattal 🟢
        - Permissions UI elkészül mock adattal 🟢
        - Projects UI elkészül mock adattal 🔴
    - API:
        - Partners graphql elkészül 🔴
- CKV 🔴
    - + hibajavítások:
        - https://linear.app/dijkstrasolution/issue/DIJ-1041/design-bugs-in-the-new-ckv-flow
        - https://linear.app/dijkstrasolution/issue/DIJ-996/hub-clears-url-search-params-on-back-navigation
- Manufacturing @Boros Barnabás
    - Tervezés szinten előáll a gyártástámogatás munkafolyamata, Árpival leegyeztetve 🔴
    - Az implementáció elindul 🔴
- Todo
    - Model beműtése a hubba @Norbert Hajdu 🟢

### DevOps

- Timlogs: 🟢
    - https://linear.app/dijkstrasolution/issue/DIJ-659/update-logged-times-from-clockify-to-dijkstra @Tamás
- https://linear.app/dijkstrasolution/issue/DIJ-1033/add-clockify-reports-to-daily-standup-meeting-memo 🟢

### Design / Marketing

- Dijkstra Marketing & PR
    - Blogok megjelenítése frontenden @Norbert Hajdu 🟢
    - Form és backend a “Request a demo”-hoz @Norbert Hajdu 🟢
        - Email kiküldése a befogadásról a requesternek és nekünk is 🟢
- Add a new user to a workspace 🟢
- Property handling in the Model viewer 🟢
- Property label on model elements 🟢
- Settings - Groups + Partners 🟢
- Technical readiness 🔴
- CKV design 🔴
```

--------------------------------------------------

## FILE: Sprint planning 3186b1ba319a8062a32ed0c9a08aa6f9.md
Source: c:\NODU\NODU technical\Sprint planning 3186b1ba319a8062a32ed0c9a08aa6f9.md
```
# Sprint planning

Category: Planning
Created by: József L. Kiss
Date: 3 March 2026

# Sprint goals

🔴🟡🟢

---

### BIM: Table view for elements

- Ability to store and retrieve history information of VSE connection server szinten @Giron Gergő 🟡
- API improvements @Giron Gergő
    - REST API kitakarítás 🟢
    - Visual Scripting Service: bináris file-ok kezelése Nexusban, CI folyamat 🟢
    - DijkstraPlatform beolvasztása a BIM.ModelServer repoba 🟢
    - Authentication támogatása 🔴
- UI @Norbert Hajdu
    - Táblázat testreszabása 🟢
    - Táblázat import/export 🟢
        - Property-k fel-le töltése 🟢
    - Napló nézet a history-hoz 🔴

### **BIM: Rhino file format support elkészül**

- Model update az új designnak megfelelően elkészül @Adrián 🟢
- Az elemek azonosítóit vizualizálni lehet a viewerben (text dot) @Giron Gergő 🔴

### BIM: Other small model-related features

- User-ek és projectek bekötése a modelleknél 🔴
- Viewer improvements @Adrián 🟢
    - Zoom to fit
    - Vágósík problémák javítása
    - Nagy modellek kezelése

### **BIM: File attachments @Bence Nemes**

- Hub-level API which supports Cloudflare storage 🟢
- Feltöltés UI-ról elkészül 🔴
- Táblázati nézte elkészül 🔴

### AI / Optimizer @Balázs Kovács

- POC: generate facade panels from textual input elkészül 🟢

### **ERP: Settings oldal elkezdése**

- HUB
    - Sentry, A hiba logolásra, de dsn hiányzik 🔴
    - Localization, mindent amit lehet fordítsuk le magyarra, és a nyelv választó részt készítsük el 🔴
- Manufacturing @Boros Barnabás 🔴
    - Tervezés szinten előáll a gyártástámogatás munkafolyamata
    - Az implementáció elindul
- Todo system 🟢
    - Model beműtése a hubba @Norbert Hajdu  🟢

### DevOps

### Design / Marketing

- Technical readiness 🟢
- CKV design 🔴 (In progress)
- PPT template 🟢
- Update model data 🔴
- Update model 🟢
```

--------------------------------------------------

## FILE: Sprint planning 45 3266b1ba319a80c58fd6fc7dd599c95a.md
Source: c:\NODU\NODU technical\Sprint planning 45 3266b1ba319a80c58fd6fc7dd599c95a.md
```
# Sprint planning 45

Created by: József L. Kiss
Date: 17 March 2026

# Sprint goals

🔴🟡🟢

---

### BIM: Table view for elements

- (Review) Ability to store and retrieve history information of VSE connection server szinten @Giron Gergő 🟢
- API improvements @Giron Gergő
    - Authentication támogatása 🟢
    - model szintű jogosultság bevezetése UI-ig 🔴
- UI @Norbert Hajdu
    - Napló nézet a history-hoz 🔴

### **BIM: Rhino file format support elkészül**

- Az elemek azonosítóit vizualizálni lehet a viewerben (text dot) @Giron Gergő 🔴
- Abort upload(user upload/process közben bezárja a tabot vagy a böngészőt —> abort alert) @Adrián 🟢

### BIM: Other small model-related features

- User-ek és projectek bekötése a modelleknél @Giron Gergő 🟡
- Model-based query for Power BI: power BI query minta elkészítése, amely kiváltja a régi status lekérdezéseket @Giron Gergő 🔴

### **BIM: File attachments**

- (Review) Feltöltés UI-ról elkészül @Bence Nemes 🔴
- Táblázati nézet elkészül @Norbert Hajdu 🔴

### **BIM: Replace the old VSE in the processes with the new VSE @Adrián** 🔴

- A panel template kreálót a VSE 2.0-ra refactorálni egy kezdetleges módon (annyit fog tudni mint a mostani)
- Külön repoba rakni??? 🟢
- UI bugfixek 🟢

### **BIM: Parametric Archicad-Revit Exchange @Bence Nemes**

- Meshed-based workflow between Archicad and Revit 🔴
- Parametric wall exchange 🔴

### AI / Optimizer

- Ability to create initial models from text @Balázs Kovács 🔴
    - OpenAI SDK validáció (agent2agent kommunikáció tesztelés) 🟢
        - Külön backend 🟢
        - UI + design 🟢
    - Minden bekötése hogy működjön élesben ami most tesztben 🔴
- Alap A+B összeadás optimalizáló elkészül szerveren @Balázs Kovács 🔴
- Optimizationhöz szükséges VSE alapfejlesztések elkészülnek @Paksi Soma 🔴
- EXTRA: Connect Timelog to test plugin “info” to AI connection (ability to append to system prompt or add MCP servers or subagents) 🟢

### **ERP: Settings oldal elkezdése**

- HUB
    - Projektek elkészülnek: 🔴
        - @Gilián Erik
            - Projekt fázis (felvétel, módosítás, törlés, hozzárendelés) 🟢
            - Address a projektekhez 🟢
            - Plugin hozzárendelhető a projekthez (még Ágival megbeszéljük ez mi is konkrétan) 🟢
        - @Tamás
            - A frontend settings/projekt része menni fog, ha megbeszéljük az appok és a financials részt Ágival 🔴
- Manufacturing @Boros Barnabás 🔴
    - Tervezés szinten előáll a gyártástámogatás munkafolyamata 🔴
    - Az implementáció elindul 🔴

### DevOps

### Design / Marketing

- Approval flow > in general [https://linear.app/dijkstrasolution/issue/DIJ-1285/design-for-approving-things-in-nodu](https://linear.app/dijkstrasolution/issue/DIJ-1285/design-for-approving-things-in-nodu)
- CKV design [https://linear.app/dijkstrasolution/issue/DIJ-1114/ckv-new-design](https://linear.app/dijkstrasolution/issue/DIJ-1114/ckv-new-design)
- Manufacturing flow [https://linear.app/dijkstrasolution/issue/DIJ-1270/manufacturing-design-draft](https://linear.app/dijkstrasolution/issue/DIJ-1270/manufacturing-design-draft)
- Design for creating a task for a model element [https://linear.app/dijkstrasolution/issue/DIJ-1191/design-for-adding-task-to-model-element](https://linear.app/dijkstrasolution/issue/DIJ-1191/design-for-adding-task-to-model-element)
- Cost code vs work phases vs tételrend [https://linear.app/dijkstrasolution/issue/DIJ-1248/settings-cost-code](https://linear.app/dijkstrasolution/issue/DIJ-1248/settings-cost-code)
- 🟢 Update model data [https://linear.app/dijkstrasolution/issue/DIJ-1203/design-for-update-model-data](https://linear.app/dijkstrasolution/issue/DIJ-1203/design-for-update-model-data)
```

--------------------------------------------------

## FILE: Sprint planning 46 3346b1ba319a8080a666cbdac85e405c.md
Source: c:\NODU\NODU technical\Sprint planning 46 3346b1ba319a8080a666cbdac85e405c.md
```
# Sprint planning 46

Created by: József L. Kiss
Date: 31 March 2026

# Sprint goals

❤️💛💚

---

### BIM: Table view for elements - ELKÉSZÜL!!!

- API improvements @Giron Gergő
    - Model szintű jogosultság bevezetése UI-ig
    - User-ek és projectek bekötése a modelleknél @Giron Gergő
- UI @Norbert Hajdu
    - Napló nézet a history-hoz

### **BIM: Rhino file format support elkészül** - ELKÉSZÜL!!!

- Az elemek azonosítóit vizualizálni lehet a viewerben (text dot) @Giron Gergő 💛

### BIM: Other small model-related features

- Model-based query for Power BI: power BI query minta elkészítése, amely kiváltja a régi status lekérdezéseket (tervezés) @Giron Gergő

### **BIM: File attachments**

- Táblázati nézet elkészül @Norbert Hajdu

### **BIM: Replace the old VSE in the processes with the new VSE @Adrián**

- Panel editor elkészül
- Rasterizer fejlesztése elindul

### **BIM: Parametric Archicad-Revit Exchange @Bence Nemes**

- Meshed-based workflow between Archicad and Revit
- Parametric wall exchange

### AI / Optimizer

- Ability to create initial models from text @Balázs Kovács
    - Minden bekötése hogy működjön élesben ami most tesztben
- Optimizationhöz szükséges VSE alapfejlesztések elkészülnek @Paksi Soma
- Alap A+B összeadás optimalizáló elkészül szerveren @Balázs Kovács
- Implement Optimizer Node (GA) on VSE basis @Balázs Kovács

### **ERP: Settings oldal elkezdése**

- HUB
    - Projektek elkészülnek:
        - @Tamás
            - A frontend settings/projekt része menni fog, ha megbeszéljük az appok és a financials részt Ágival
    - Invite user elkészül
    - 
- Manufacturing @Boros Barnabás
    - n8n-es implementáció 50%-os állapotra eljut, dummy UI-al (???)

### DevOps

- Migrate infra services to new server (https://linear.app/dijkstrasolution/issue/DIJ-1297/migrate-infra-services-to-new-server)
- Ability to operate test environments (https://linear.app/dijkstrasolution/issue/DIJ-1275/ability-to-operate-test-environments)-hez készüljön el egy stratégia

### Design / Marketing

- Approval flow > in general [https://linear.app/dijkstrasolution/issue/DIJ-1285/design-for-approving-things-in-nodu](https://linear.app/dijkstrasolution/issue/DIJ-1285/design-for-approving-things-in-nodu)
- CKV design [https://linear.app/dijkstrasolution/issue/DIJ-1114/ckv-new-design](https://linear.app/dijkstrasolution/issue/DIJ-1114/ckv-new-design)
- Manufacturing flow [https://linear.app/dijkstrasolution/issue/DIJ-1270/manufacturing-design-draft](https://linear.app/dijkstrasolution/issue/DIJ-1270/manufacturing-design-draft)
- Design for creating a task for a model element [https://linear.app/dijkstrasolution/issue/DIJ-1191/design-for-adding-task-to-model-element](https://linear.app/dijkstrasolution/issue/DIJ-1191/design-for-adding-task-to-model-element)
- Cost code vs work phases vs tételrend [https://linear.app/dijkstrasolution/issue/DIJ-1248/settings-cost-code](https://linear.app/dijkstrasolution/issue/DIJ-1248/settings-cost-code)
- 🟢 Update model data [https://linear.app/dijkstrasolution/issue/DIJ-1203/design-for-update-model-data](https://linear.app/dijkstrasolution/issue/DIJ-1203/design-for-update-model-data)
```

--------------------------------------------------

## FILE: RN_45.txt
Source: c:\NODU\NODU technical\Release notes\RN_45.txt
```
# 31 March 2026

<aside>
💡

**TL;DR**

---

### Product Development & Agentic AI

- **Agentic AI & MCP:** Integrated schema changes to support AI agent extensions, allowing the Hub’s chat interface to connect to plugins via **Model Context Protocol (MCP)**.
- **Model Enhancements:** Redesigned the "extra properties" loading flow and implemented **text-dot labels** for better data visualization in the model viewer.
- **VSE & Data History:** Established a version history for the Visual Scripting Engine and upgraded backend callbacks to track and return model element changes.

---

### Infrastructure & ERP Integration

- **Permissions & Security:** Built a comprehensive backend system for granular user/plugin permissions and added an "Abort Upload" safety pop-up to prevent data loss.
- **System Stability:** Cleaned up the **Drizzle ORM** logic to handle heavy data modifications and resolved core FDB maintenance issues like NKE data exports.
- **Internal Tools:** Fixed **Clockify synchronization** and optimized repository tracking for internal development teams.

---

### UI/UX & Reliability

- **UX Refinement:** Processed user feedback from UX testing to improve the Nodu model viewer’s interface and navigation.
- **Bug Fixes:** Resolved technical debt regarding component resizing, list sorting, and VSE connection logic.
</aside>

## Dijkstra models

- UX test > some UX feedback and wishes about the current Nodu model viewer
- Update Model data > new design for loading extra properties for model elements
- VSE History - https://dbdiagram.io/d/V3-69984b22bd82f5fce24bf709

![image.png](attachment:bfe11466-72e5-4127-a113-b7ff2cd7071d:image.png)

- Show labels in model viewer > using text dots

![image.png](attachment:f66e010d-0829-4b18-8166-f2dc480171bd:image.png)

- 🐞 Minor bugs > resize, sorting, drop-down bugs
- VSE Connection
- More data for callbacks > a model element history-val kapcsolatos backend fejlesztés. A változásokról küld vissza adatot a rendszer
- Abort upload option > when the user tries closing the window accidentally, then the browser shows a security pop-up with an “Are you sure…?” type of question.

![image.png](attachment:1678764d-5555-48ff-aa37-5a13272acc5e:image.png)

## Agentic AI

- Schema changes to handle agent extensions
- AI chat interface in HUB > from now on, Nodu’s AI chat can connect to plugin AI agents through their MCPs

![image.png](attachment:f4a46a42-9406-4d6c-a492-19f76c2f1c54:image.png)

![image.png](attachment:299c6920-7102-4403-aa35-0fa96eb42780:image.png)

## Core FDB maintenance

- 🐞 NKE data table export by strings > minor fix based on user feedback

## Dijkstra ERP Integration

- Permission system backend > users, groups, plug-in, project phases, projects, etc
- 🐞 Drizzle (a database handler system we use) upload issue > due to many data modifications on the backend, it needed a bigger cleaning to handle the situation
```

--------------------------------------------------

## FILE: RN_46.txt
Source: c:\NODU\NODU technical\Release notes\RN_46.txt
```
# 14 April 2026

<aside>
💡

**TL;DR**

---

#### Interoperability & Data Exchange

- **Parametric Archicad-Revit Exchange:** Enabled native-to-native parametric wall exports from Archicad to Revit, ensuring geometric crossover remains intact during format conversion.
- **VSE Performance:** Improved Python evaluation logic and established a dedicated development environment to accelerate data translation between BIM authoring tools.
- **Generator Nodes:** Introduced VSE generator nodes to automate the creation of native elements across different platforms.

---

#### Agentic AI & ERP Integration

- **Agentic Backend:** Implemented a new AI agent framework using the **Google ADK**, allowing multiple agents to collaborate on tasks with a set of default backend tools.
- **Advanced Permission System:** Launched a comprehensive UI for managing users, partner groups, and project phases, including granular control over app access and workspace permissions.
- **Localization & Personalization:** Added a Hub language switcher (EN/HU), customizable login themes, and support for project-specific postal addresses.

---

#### Model Viewer & UX Improvements

- **Data Visualization:** Updated the viewer UI to support "text dot" labels, allowing users to display selected properties directly on model elements.
- **Attachment Core:** Finalized the functionality and UI for model attachments, enabling universal file linking across the Nodu ecosystem.
- **Table History:** Added a frontend history view for data tables and updated the global selection widget to improve bulk data management.

---

#### Infrastructure & Facade Modeling

- **Platform Stability:** Migrated infrastructure services to a new sub-server architecture to optimize performance and scalability.
- **Facade Editor:** Developed the frontend for the new Panel Editor and integrated built-in nodes for the updated VSE (Rete-based) logic.
- **Technical Audit:** Completed an investigation into the *Portia* Grasshopper plugin, concluding its graph-model approach is not currently relevant to the Nodu roadmap.
</aside>

## Parametric Archicad-Revit Exchange

DIJ-1280: Export parametric wall data from Archicad

DIJ-1281: Convert to RevitWall with generators

- Ability to import parametric walls from Archicad to Revit
- Currently properties don’t carry over, but crossover between native formats is solved
    
    ![image.png](attachment:031c62b1-f2f8-4e05-9ec1-796cf686b96d:image.png)
    
    ![image.png](attachment:a1c03543-feec-449b-8fee-390358ce1f1f:image.png)
    

## Optimization

DIJ-1278: VSE development environment

DIJ-1265: VSE evaluation Python improvements

Ezekkel a fejlesztésekkel az adatfordítás (pl Archicad-Revit és fordítva) könnyebb és gyorsabb

DIJ-1195: VSE generator node

## Dijkstra models

DIJ-1289: Viewer extra data - UX update

![image.png](attachment:a30c001a-17dd-4975-8f38-598479ff8a58:image.png)

DIJ-1245: Remaining attachment features + DIJ-1249: Attachments core functionality

![image.png](attachment:ed5e6ea5-497e-494b-ae17-e9b2c4b71638:image.png)

DIJ-1166: Table view frontend history

![image.png](attachment:c79718e9-2ad7-43cd-beee-a37954207a54:image.png)

DIJ-1151: Show labels in model viewer (text dot) > Show the selected property on model elements

![image.png](attachment:25495c25-a48e-4b19-afab-4aed4ac9eb9d:image.png)

## Simple facade modeling

- 🐞 DIJ-1292: VSE invalidate slots
- DIJ-1288: Rete for new VSE, DIJ-1286: Frontend for Panel editor, DIJ-1284: Built-In nodes

![image.png](attachment:56706bff-4ee9-43e8-bc61-cd72cb185f02:image.png)

## Agentic AI

- DIJ-1279: Agentic backend using Google ADK > AI agents coworking

![image.png](attachment:2f3a9edd-011a-4d32-b68e-ce89852e5c73:image.png)

- DIJ-1303: Default tools in backend agent

## Dijkstra ERP Integration

- DIJ-1018: Change background image > when logging in using the theme settings
- DIJ-1283: Project phases and postal address
- DIJ-987: Permission system UI for hub and QR code plugin
- DIJ-1137: Settings > UI and backend for members, users, permissions
    - Updated the settings page.
    - Members:
        - Can add to Groups, Projects, and Apps. Can add Permission to user aswell.
    - User Groups
        - Can create new user group, and a partner group with three addresses.
        - Modify Group and delete groups.
        - Add or remove Apps, Users, and Projects to Groups
        - Modifying Permissions to Groups
    - Permissions
        - A permission overview
        - Can add or remove Users or Groups to Permissions
    - Projects
        - Can create new Projects
        - Modify or Delete Projects, with address
        - Can add or remove Users, Groups, or Apps

![image.png](attachment:bf681ebb-0971-4469-bcee-0d7f8fae64bb:image.png)

- DIJ-1176: data table global select > update the table UI widget so it knows this new function

![image.png](attachment:804a68e4-979c-43f1-93bc-3eba5ea68798:image.png)

## Internal Tools

- DIJ-1192: Hub localization switch > now it is possible to switch beween Hungarian and English

![image.png](attachment:c6bd16c4-d551-47ca-9bf0-6dfe5fe7feca:image.png)

- DIJ-1297: Migrate infra services to new server > main server improvements by outsourcing to subservers

![image.png](attachment:b5f8ccf4-96e8-4845-868a-e268fe8dea5f:image.png)

- DIJ-1131: Repos of GG > all the strings have an English and Hungarian version in our own repositories
```

--------------------------------------------------

## FILE: bridge-waitlist.html
Source: c:\NODU\NODU Bridge Repo\bridge-waitlist.html
```
N
NODU Bridge
Korai hozzáférés
Archicad modellek Revitbe, a
paraméterek
elvesztése nélkül
A NODU Bridge az elemek logikáját viszi át Archicad és Revit között, nem pusztán a statikus geometriát. Iratkozz fel a korai hozzáférési listára, és szólunk, amint elérhető.
Parametrikus átültetés natív mapping alapján, nem nyers IFC-export.
Kevesebb kézi utómunka: megmaradnak a paraméterek és az elemtípusok.
A feliratkozók elsőként próbálhatják ki, és alakíthatják a fejlesztést.
Az első 100 feliratkozó
év végéig ingyenes keretet kap a Bridge használatához.
Feliratkozás a korai hozzáférésre
Néhány adat segít, hogy a számodra fontos problémával kezdjük.
Email
*
Név
Szerepkör
Válassz
BIM Coordinator
BIM Manager
Építész
Egyéb
Mi a legnagyobb nehézség az Archicad–Revit munkafolyamatodban?
Hozzájárulok, hogy a NODU felvegye velem a kapcsolatot a Bridge korai hozzáférésével kapcsolatban.
Adatkezelési tájékoztató
Feliratkozom a korai hozzáférésre
Valami nem sikerült. Kérjük, próbáld újra, vagy írj a poczai@nodu.build címre.
Megerősítő emailt küldünk; csak a megerősítés után veszünk fel a listára.
Köszönjük a feliratkozást
Küldtünk egy megerősítő emailt. Kérjük, kattints a benne lévő linkre, hogy véglegesítsd a feliratkozást. Amint a Bridge elérhető, elsők között szólunk.
NODU Bridge · nodu.build
```

--------------------------------------------------

## FILE: nodu-bridge-esettanulmanyok.html
Source: c:\NODU\NODU Bridge Repo\nodu-bridge-esettanulmanyok.html
```
Belső stratégiai dokumentum
Enterprise esettanulmányok: három különböző konverziós trigger
Három nyilvános enterprise eset egy AEC adatplatform körül azt mutatja: az enterprise konverzió nem egyetlen okból következik be, a három kiváltó ok három különböző vásárlói profilt fed le. Ezek iparági analógiák a mechanizmus megértésére, nem NODU-referenciák.
Belső stratégiai dokumentum
2026-06-15
Forrás: nyilvános AEC projektleírások és iparági közlemények
Az esettanulmányok funkciója és korlátai
A három eset egyike sem véletlenül Enterprise-előfizető. Mindhárom esetben egy technikai szakember (BIM-koordinátor, computational lead vagy technológiai vezető) volt az, aki elsőként vezette be az eszközt, majd megteremtette a feltételeket a szervezeti szintű belépéshez. Ez a „beachhead” minta: a szakember megoldja a közvetlen problémáját, a szervezet megismeri a platformot, az Enterprise döntés utólag követi.
Ezek az esettanulmányok egy konkrét elemzési célt szolgálnak: megérteni, hogy mi váltotta ki az ingyenes szintről az Enterprise szintre való átlépést olyan irodáknál, amelyek egy nyílt AEC adatplatformot már bevezettek. A kérdés nem az, hogy „miért szerették a platformot”, hanem az, hogy „mi tette az ingyenes szintet elégtelenné”.
A leírások az adott platform saját publikált anyagaiból, konferencia-előadásokból és iparági sajtóból származnak. Ez túlélési torzítást (survivorship bias) jelent: a nyilvánosság elé kerülő esetek azok, ahol az eredmény pozitív volt. Azokhoz az esetekhez nem férünk hozzá, ahol a bevezetés sikertelen volt, vagy ahol az irodák visszatértek az ingyenes szintre. Az enterprise kimenetelek tényleges eloszlása ismeretlen.
A három esetből nem tudjuk a ténylegesen kifizetett szerződéses árat, a bevezetési ütemezést, a belső ellenállást, az Enterprise-döntés időpontjában aktív felhasználók számát, sem azt, hogy az iroda megújította-e a szerződését. Az elemzési érték a kiváltó mechanizmusban rejlik, nem a kereskedelmi részletekben.
Jövőbeli irányként megjegyzendő: ha a VSE-alapú parametrikus tartalomkészítési képesség egyszer elérhetővé válik, egy párhuzamos belépési profil is megjelenhet: a tartalomalkotó, aki nem adatcserével, hanem többformátumú parametrikus tartalom (Revit Family és további CAD-/gyártói formátumok) tervezésével kezd. Az induláskor azonban ez a profil nem létezik, az alábbi esettanulmányok kizárólag az adatcsere-alapú adaptációt elemzik.
Cég
Projekt típus
Enterprise trigger kategória
Felhasznált funkció
ARUP
Multidiszciplináris infrastruktúra
Jogi / szerződéses kényszer
SSO, RBAC, dedikált szerver
Ramboll
Automatizált szerkezeti tervezés
Számítási kapacitás
Szerver-oldali automatizálás (Enterprise keret)
Herzog & de Meuron
Egyedi szoftver integráció
Szellemi tulajdon védelme
Privát szerver, elzárt munkaterek
01 ARUP
ARUP: amikor az adatszuverenitás nem IT-szabály, hanem szerződéses kötelezettség
Az ARUP eset egy nagy, multidiszciplináris infrastrukturális projektet érint Hongkongban. A csapatstruktúra jellegzetes: az ARUP vezet belső szerkezeti, MEP és homlokzatmérnökökkel, miközben több külső tervező partner biztosítja a diszciplína-specifikus modelleket. A projekt léptéke és földrajzi összetettsége nem véletlen. Ezek teszik az adatkezelési problémát éles kérdéssé.
Ilyen projekten az adathozzáférés-kezelés nem belső preferencia kérdése, hanem szerződéses követelmény. A különböző külső közreműködőknek különböző jogaik vannak a modell különböző rétegeihez. Egy külső iroda szerkezeti mérnöke nem láthatja a szabadalmaztatott homlokzati részleteket. Egy MEP-alvállalkozó nem kaphat írási jogot a szerkezeti modellhez. Az ilyen platformok közösségi (ingyenes) szintje a tervezésénél fogva nem biztosítja azt a részletes hozzáférés-kezelést, amely e határok betartatásához szükséges.
Ez lényeges megkülönböztetés a NODU Bridge paywall-elemzéshez. Az ARUP nem azért lépett Enterprise szintre, mert az IT osztályuknak biztonsági szabályzata volt. Azért léptek, mert a projektszerződés megkövetelte a demonstrálható adathozzáférés-kezelést. A döntést jogi és beszerzési szint vezérelte, nem a mérnöki csapat.
Amire ténylegesen szükségük volt: dedikált felhőkörnyezet (az adatok nem élnek megosztott nyilvános szerveren), SSO-integráció (a külső közreműködők a saját szervezeti hitelesítő adataikkal lépnek be, a hozzáférés visszavonható, amikor egy megbízás véget ér), részletes RBAC (szerepmeghatározások diszciplína és projektfázis szerint), valamint auditnapló (annak bizonyítéka, hogy ki mikor mihez fért hozzá).
Az ARUP eset a NODU Bridge potenciális Enterprise ügyfeleinek egy konkrét szegmensére vetíthető: olyan irodákra vagy BIM-koordinátorokra, akik több külső közreműködőt kezelnek egyetlen projekten belül. A kiváltó ok nem az iroda mérete, hanem az együttműködési struktúra. Egy kisebb iroda, amely 5 külső homlokzati szakértőt koordinál, ugyanolyan szerződéses adatkezelési követelménnyel szembesülhet.
Amit nem tudunk
Nem ismert, hogy az ARUP esetében a döntést a projekt BIM-menedzsere, a jogi osztály vagy a beszerzési osztály hozta. Ez azért releváns, mert a különböző döntéshozó profilok különböző értékesítési megközelítést igényelnek.
02 Ramboll
Ramboll: ahol nem a biztonság, hanem a számítási kapacitás volt a trigger
A Ramboll „Soufflé” projektje automatizált szerkezeti tervezést és végeselem-analízist (FEA) foglalt magában csőhidak esetében. Ez parametrikus mérnöki munkafolyamat: a tervezési teret számítógéppel tárják fel, nem kézzel modelleznek egyszerre egy variánst. A csapat több száz szerkezeti variánst generál, amelyek mindegyike automatizált FEA-validálást igényel. A platform szerveroldali automatizálási szolgáltatását használták a futtatáshoz.
Ez a szerveroldali automatizálás Community szinten számítási kredit-limitet tartalmaz. Egy olyan munkafolyamatban, amely folyamatos parametrikus felfedezést futtat (generálja, értékeli és elveti a variánsokat automatizált ciklusokban), a Community-kredit gyorsan elfogy. A munka nem szünetelhet egy számlázási cikluson át. Ez nem biztonsággal vagy hozzáférés-kezeléssel kapcsolatos, tisztán számítási áteresztőképességről van szó.
A Ramboll eset alapvetően más Enterprise döntést képvisel. A döntéshozó a projektmérnök vagy a számítástechnikai tervezési vezető, nem a jogi vagy IT osztály. Az értékajánlat közvetlen: „az automatizált pipeline-unk X órát fut hetente, Y napon belül meghaladja a Community kredit-limitet, az Enterprise szint Z kreditet biztosít.” Ez lényegesen egyszerűbb ROI-kalkuláció, mint az ARUP esetben.
Ez az eset releváns a NODU Bridge számára, mert validálja a parametrikus motort mint értékhajtót. A Ramboll nem fájlok átvitelére használja a platformot, hanem a parametrikus tervezési folyamat infrastruktúrájaként. Minél mélyebben beágyazott a parametrikus munkafolyamat, annál magasabb a fizetési hajlandóság a megszakítatlan végrehajtásért. A NODU Bridge Vizuális Script Engine hasonló függőséget teremt: azok az irodák, amelyek összetett leképezési scripteket építenek ismétlődő projekttípusokhoz, garantált hozzáférést fognak akarni.
A Ramboll eset nem vetíthető közvetlenül a NODU Bridge Professional szintjére: a jelenlegi kialakításban a Professional szint seat-alapú, nem számításalapú. Egy kérdést azonban felvet: ha az irodák automatizált konverziós pipeline-okat építenek a NODU Bridge API-jával (Studio szinttől elérhető), egy API-hívás-korlát természetes frissítési kiváltóvá válhat a Studio-ból az Enterprise-ra. Ezt érdemes nyomon követni az első 12 hónapban.
Amit nem tudunk
Nem ismert, hogy a Ramboll-projekt mekkora volt, hány automatizálási futtatást igényelt hetente, és hogy a Community tier pontosan mikor bizonyult elégtelennek. A „számítási kapacitás mint trigger” hipotézis ezekre a részletekre épülne, ha a NODU Bridge esetében alkalmaznánk.
03 Herzog & de Meuron
Herzog & de Meuron: a saját szoftver és az IP-védelem mint elsődleges motiváció
A Herzog & de Meuron egy saját fejlesztésű életciklus-értékelési (LCA) eszközt integrált a BIM-adatpipeline-jükbe. Az LCA-szoftvert belső fejlesztéssel hozták létre, amely évnyi módszertani befektetést tükröz, és versenyképes megkülönböztetőt jelent az iroda számára. Az integráció lehetővé tette az irodának, hogy fenntarthatósági elemzést futtasson közvetlenül a BIM-adatpipeline-jükben.
Egy saját algoritmus futtatása megosztott, közösségi szerverkörnyezeten keresztül azt jelenti, hogy az eszköz kimenetei, esetleg bemenetei és logikája is megosztott infrastruktúrán léteznek. Egy olyan iroda számára, amely jelentősen befektetett egy saját módszertan kidolgozásába, ez IP-kitettséget teremt. Az aggodalom nem a hagyományos értelemben vett adatszivárgásról szól, hanem arról, hogy a saját algoritmusok nem futhatnak megosztott infrastruktúrán.
Az ARUP eset külső szerződéses követelményeknek való megfelelésről szólt. A H&dM eset belső versenyelőny védelméről szól. Ezek strukturálisan különböző motivációk. A megfelelés küszöbkövetelmény: vagy teljesíted, vagy nem tudod használni az eszközt. A versenyelőny-védelem stratégiai választás: az iroda elméletileg elfogadhatná a kockázatot, de nem teszi. A fizetési hajlandóság logikája ezért más: a saját algoritmus érzékelt értékéhez kötődik, nem szerződéses kötelezettséghez.
Amire ténylegesen szükségük volt: privát szerver (az LCA-eszköz elszigetelt környezetben fut), munkaterület-hozzáférés-kezelés (csak az arra felhatalmazott belső csapattagok indíthatják el az LCA-integrációt), és a lehetőség, hogy az iroda saját adatfeldolgozása lecsatolható legyen a megosztott, nyilvános infrastruktúráról.
Ez az eset releváns a NODU Bridge számára azon irodáknál, amelyek fejlett leképezési scripteket fejlesztenek. Egy homlokzatszakértő iroda, amely 12-18 hónap alatt összetett parametrikus leképezési könyvtárat épít fel, szellemi tőkét hoz létre a NODU Bridge környezetben. A kérdés, hogy ez az IP hol él (a NODU megosztott felhőjén vagy az iroda saját infrastruktúráján), stratégiailag relevánssá válik, ahogy a script könyvtár érik. Ez egy lassan kialakuló Enterprise trigger: nem jelenik meg az első napon, hanem ahogy az iroda platform-befektetése növekszik.
Amit nem tudunk
Nem ismert, hogy a H&dM LCA-integráció milyen mélységű volt, és hogy az IP-védelem aggálya a technológiai vezető vagy a menedzsment szintjéről érkezett. Az egyik esetben gyorsabb, a másik esetben sokkal lassabb értékesítési ciklust jelent.
04 Összehasonlítás
Három eset, három különböző trigger összehasonlítás
A három eset egy közös jellemzőt oszt: mindhárom nagy, kifinomult iroda bevett BIM-munkafolyamattal. Az Enterprise konverzió mindhárom esetben azután következett be, hogy az iroda már beépítette a platformot a munkafolyamatába (az ingyenes szint elegendő volt a kezdeti bevezetéshez), és a kiváltó ok egy konkrét projekt- vagy stratégiai szükségletből alakult ki, amelyet az ingyenes szint nem tudott kielégíteni. A konverziókat nem funkciófelismerés vezérelte, hanem egy konkrét működési korlátba való ütközés.
A három kiváltó ok kategorikusan különböző: jogi/szerződéses (ARUP), számítási kapacitás (Ramboll), IP védelem (H&dM). Mindegyik különböző vásárlói profilt, döntési időtávot és értékesítési megközelítést implikál. A megfelelési trigger gyorsan mozoghat, miután a szerződéses követelmény azonosítva van. A kapacitási trigger egy projekt életciklusát követi. Az IP trigger stratégiai és lassan mozgó.
Dimenzió
ARUP
Ramboll
H&dM
Trigger kategória
Jogi/szerződéses kényszer
Számítási kapacitás
Szellemi tulajdon védelme
Döntéshozó (feltételezett)
Jogi/beszerzési osztály
Projekt mérnök / computational lead
Technológiai vezető / menedzsment
Döntési időtáv
Gyors (szerződéses kötöttség)
Projekt-követő (kapacitásigény alapján)
Lassú (stratégiai)
Trigger megjelenési idő
Projekt indulásakor
Workflow elmélyülésekor
Platform-befektetés növekedésekor
Elsődleges Enterprise funkció
SSO + RBAC + dedikált szerver
Automate Enterprise keret
Privát szerver / on-premise
Free tier miért nem elég
Hozzáférés-kezelés nem granulált
Compute limit
Megosztott infrastruktúra
ROI kalkulálhatósága
Közvetett (compliance cost)
Közvetlen (compute hours)
Közvetett (IP érték)
A fenti táblázat feltárja, hogy az „enterprise konverzió” nem egyetlen jelenség. Legalább három különböző jelenség, amelyek véletlenszerűen ugyanolyan kereskedelmi eredményre jutnak. Ennek közvetlen következményei vannak a NODU Bridge Enterprise piacra lépési stratégiájára: egyetlen általános Enterprise-értékajánlat kevésbé lesz hatékony, mint a kiváltó-specifikus üzenetküldés.
A platform-belépés mint negyedik trigger
Az ARUP, Ramboll és H&dM esetei compliance-, kapacitás- és IP-triggert mutatnak. Van egy negyedik trigger, amely a NODU Bridge-nél különösen releváns: a platform-belépés.
Az Enterprise Bridge-előfizető hozzáfér a NODU platform-funkcióihoz (BIG graph, ERP integráció, constraint optimizer). Azok az irodák, amelyek már a Bridge-et intenzíven használják és komplex mapping script könyvtárat építenek, természetes lépésként mélyítik a platform-kapcsolatot. Ez a trigger lassan alakul ki az iroda platform-befektetésével arányosan, de strukturálisan a legmagasabb LTV-t eredményezi.
Egy lehetséges ötödik trigger, jövőbeli irány: a saját parametrikus tartalomkönyvtár mint IP-eszköz
A fenti négy trigger az indulási termékkörre vonatkozik. A VSE-alapú parametrikus tartalomkészítés egy későbbi fejlesztési irány: ha egyszer elérhetővé válik, egy ötödik trigger is kialakulhat. Az iroda, amely saját parametrikus tartalomkönyvtárat épít fel, szellemi vagyont halmozna fel hasonlóan a mapping script könyvtárhoz, de egy dimenzióval mélyebben: a könyvtár az iroda parametrikus tervezési tartalmát tárolja, és mivel a képesség a 2026-07-06-i pontosítás szerint többformátumú, ugyanaz a definíció Revit Family-ként, Archicad-, IFC- vagy más formátumban is kiadható, licencelhető, értékesíthető vagy partnereknek kiosztható. Az egyetlen definícióból sok formátum elv az IP-érvet erősíti: a felhalmozott tartalom értéke nem egy célszoftverhez kötött. Ez strukturálisan erős Enterprise trigger lehetne, különösen a homlokzat-specialista és dizájnintenzív irodáknál. Mindez azonban nem része az indulási termékkörnek, és a jelenlegi számítások nem kalkulálnak vele.
05 Nyitott kérdések
Nyitott kérdések: mit mondanak ezek az esetek a NODU Bridge számára
Az alábbi kérdések szándékosan nincsenek megválaszolva ebben a dokumentumban. Megválaszolásuk az első enterprise értékesítési ciklusok adatai alapján lehetséges, előtte bármilyen válasz spekulatív lenne.
01
Melyik Enterprise trigger profil releváns a NODU Bridge első célszegmensében?
A NODU Bridge 2026-os célszegmense (kis- és közepes tervező-kivitelező irodák, homlokzati specializáció) nem egyezik teljesen egyik esettanulmány-profillal sem. Az ARUP nagy, multidiszciplináris infrastrukturális kontextust feltételez. A Ramboll fejlett parametrikus tervezési kultúrát igényel. A H&dM érett platform-befektetést. Kérdés: a NODU Bridge első Enterprise ügyfelei melyik profil felé gravitálnak?
Egy várható minta: a kisebb, de ambiciózusabb irodák BIM-koordinátora inkább a kapacitás- vagy IP-triggert fogja mutatni. A nagyobb, projektvezérelt irodák inkább a compliance-triggert. A platform-trigger mindkét profilban megjelenhet, de csak azután, hogy az iroda már 6-12 hónapja aktívan használja a Bridge-et.
02
A script engine létrehoz-e IP-védelmi igényt, és ha igen, mikor?
A H&dM esetéből következik: ha egy iroda 12-18 hónap alatt épít fel egy komplex mapping script könyvtárat, az a NODU Bridge-ben tárolt szellemi tőkét képvisel. Kérdés: melyik az az értékhatár vagy időtáv, amelynél az iroda számára stratégiai kérdéssé válik, hogy ez a script könyvtár hol tárolódik? Jövőbeli irányként ez a kérdés a Revit Family könyvtárra fokozottabban is felmerülhet, ha a Family-tervezés egyszer bekerül a termékbe. Az induláskor azonban kizárólag a mapping script könyvtárra vonatkozik.
03
A Community-ból Professional frissítési kiváltó elegendő-e, vagy az Enterprise trigger az első éles korlát?
Az esettanulmányok mind Enterprise-szintű konverziókat mutatnak, az intermediate tier dinamikájáról a nyilvános esetekből sincs adatunk. Kérdés: a KKV-piacon az első éles fizetési korlát a Professional tier (sablonmentés + élő szinkron) lesz-e, vagy egyes ügyfelek a Community-ból közvetlenül Enterprise-ra ugranak, ha a compliance trigger elég erős?
04
A három enterprise profil közül kettő lassan mozgó döntési ciklust feltételez: hogyan finanszírozza a NODU Bridge ezt az időtávot?
Az IP-védelmi és a szerződéses compliance trigger jellemzően 6-12 hónapos értékesítési ciklust jelent. Ha a NODU Bridge Enterprise ügyfelei főként ezekbe a kategóriákba esnek, a bevételtervnek ezen a szinten konzervatívan kell kalkulálnia. A Professional és Studio tier gyorsabb konverziójának kell finanszíroznia az Enterprise pipeline fejlesztését.
05
A gyártói szegmens go-to-market logikája: a kérdésre már van kidolgozott válasz-vázlat
Ez a kérdés a 2026-06-11-i NODU Creator (Content Engine) blueprint v2.0-val részben megválaszolódott: a gyártói szegmens nem a Bridge licencstruktúrájára illesztendő, hanem önálló termékpályát kap: knowledge-graph-alapú termékadat-motor, saját árazással (Starter/Growth/Enterprise, €3–50k/év platform fee + generálási díj), sales-vezérelt pilot-GTM-mel, és többformátumú kimenettel (a Revit Family csak egy export a sok közül). A vezetőség az irányt támogatja, a részletes kidolgozás későbbre ütemezett. Ami nyitott marad: a Bridge-en belüli VSE-tartalomkészítés (iroda-oldali képesség) és a Creator (gyártói termék) közös generálási magjának határvonala, vagyis hogy mely komponens él melyik termékben, és hogyan kerülik el a kettős fejlesztést.
A Platform-belépés mint hosszú ciklusú trigger
A Bridge -> Platform Core upsell nem az első napon következik be. Az iroda először a közvetlen problémát oldja meg (adatcsere), majd megismeri a platform többi funkcióját, majd ha a BIM-koordinátor vagy a principál látja az értéket, mélyíti a kapcsolatot. Ez 12-24 hónapos ciklus, amelyet aktív customer success munkával lehet rövidíteni. Nem szabad feltételezni, hogy organikusan kialakul.
Ezek a kérdések az első 3-5 Enterprise tárgyalási folyamat során válaszolhatók meg, előtte nem.
```

--------------------------------------------------

## FILE: nodu-bridge-lead-gen.html
Source: c:\NODU\NODU Bridge Repo\nodu-bridge-lead-gen.html
```
N
NODU Bridge
Bizalmas, belső
Sales infrastruktúra, 2026
Célzott lead-generálás
Archicad–Revit
fájdalompontok alapján
Egy rendszer, amely két irányból azonosítja azokat a BIM-szakembereket, akiknek gondot okoz az Archicad-modellek Revitbe történő parametrikus migrációja: figyeli a nyilvános szakmai közösségeket, és a nodu.build/bridge oldalon közvetlenül is gyűjti az érdeklődőket. A leadek automatikusan a NODU Sales CRM-be kerülnek (a saját, account-centrikus rendszerünkbe — a Pipedrive kikerült a láncból), hogy 2026 végéig minél több lehetséges NODU Bridge-felhasználót érjünk el, majd az ingyenes időszak lejárta után, 2026. december 31-ig legalább 10 fizetős ügyfelet szerezzünk. A teljes rendszer (nodu-monitor, ingest-adapter, NODU Sales) nem csak a Bridge-hez épül — a fájdalompont-figyelés és a lead-generálás logikája később a NODU platform egészére is kiterjeszthető lesz.
Státusz
Kód kész, n8n-bekötésre vár
Felelős
Poczai Zoltán, sales
CRM
NODU Sales (saját, account-centrikus)
Automatizáció
n8n → POST /api/bridge/ingest
Dokumentum dátuma
2026. június 30. · frissítve 2026-07-12
Rendszer áttekintés
A lead-generálás négy fő mutatója
5
Aktív adatforrás
Reddit, Playwright, Stack Overflow, Google CSE, HTML-fórumok
5 / 7
Relevancia-küszöbök
Score ≥ 5: Lead-deal, score ≥ 7: Qualified-deal a NODU Salesben (env-konfig, A/B-teszt alatt)
Most
Waitlist és RB2B élesítés
A nodu.build/bridge feliratkozás és az RB2B ingyenes látogató-azonosítás már most indul
10
Fizetős ügyfél, cél
Az ingyenes időszak lejárta után, 2026. december 31-ig
Stratégia
A rendszer két forráscsatornája
A BIM-szakemberek kétféleképpen jelennek meg a látóterünkben: aktívan kérdeznek egy szakmai fórumon, vagy a nodu.build/bridge oldalunkon járnak. Az első csoportot a
nodu-monitor
találja meg — egy önállóan (cron-jobként) futó Python-alkalmazás, amely a nyilvános BIM-közösségi fórumokat figyeli és pontozza a releváns bejegyzéseket; a másodikat a weboldal: önkéntes waitlist-feliratkozással vagy az RB2B látogató-azonosítással.
nodu-monitor
közösség-figyelés
Aktív
Mi ez:
egy önállóan (cron-jobként) futó Python-alkalmazás, amely a forrás típusától függő ütemben olvassa a BIM-közösségek nyilvános tartalmát — a Reddit-figyelés valós idejű, a többi forrást 90 percenkénti ciklusban járja körbe. Ha valaki az Archicad–Revit átültetésről ír, problémát említ vagy segítséget kér, a bejegyzést a rendszer 25+ kulcsszó alapján pontozza (elsődleges kifejezés 3 pont, fájdalompont-jelző 2 pont, kontextus-szó 1 pont), és duplikátum-szűréssel a saját SQLite adatbázisába menti. A releváns posztokhoz a rendszer Claude API segítségével válaszjavaslatot készít, amelyet a sales kolléga Slack-en egy 👍/👎 gombbal hagy jóvá, mielőtt kézzel kiküldi.
Reddit (PRAW)
r/Revit, r/ArchiCAD, r/BIM, valós idejű
Playwright (Chromium)
Graphisoft Community, Autodesk Community (JS-alapú oldalak)
Stack Overflow API
revit+archicad, revit+ifc; ingyenes, 300 kérés/nap
Google CSE
RevitForum, BuildingSMART fórumok
HTML scraping
Statikus phpBB alapú fórumok
nodu.build/bridge
weboldal
Most induló
A weboldal kétféleképpen szerez leadet. A waitlist-űrlapon az érdeklődő önként megadja az e-mail-címét, a szerepkörét és a fő Archicad–Revit fájdalompontját; ez a NODU Sales „Bridge Waitlist" kampányába kerül (Registration lépcső), így a tölcsér-riport ingyen méri a konverziót. Az első 100 feliratkozó év végéig ingyenes keretet kap, ami erős ösztönző a korai jelentkezésre. Emellett az RB2B snippet azonosítja az anonim látogatókat: az ingyenes csomag már most bekapcsolható, a teljes, automatizált azonosítás a Pro csomaggal és az éles weboldali forgalommal érkezik.
Waitlist-feliratkozás
E-mail, név, szerepkör, fő fájdalompont
Lead-minősítés
A fájdalompont alapján pontozott, meleg lead
Egyenes út
n8n → NODU Sales „Bridge Waitlist" kampány
RB2B ingyenes (most)
Anonim látogató, USA, cégszint, Slack-értesítés
RB2B Pro (szept.)
Személyszint, webhook, automatikus NODU Sales (email-domain verify, no-PII)
A célrendszer
SalesOS: a NODU Sales CRM, ami fogadja és kezeli a leadeket
A NODU Sales (fejlesztői munkanevén SalesOS) egy saját fejlesztésű, account-centrikus, AI-natív CRM — nem harmadik féltől vásárolt eszköz, mint a korábban használt Pipedrive, hanem kifejezetten a NODU sales-munkafolyamatára épített rendszer. Minden adat egy cég köré szerveződik (dosszié-nézet: kontaktok, activity-történet és dealek egy helyen), a felület billentyűzet-first (globális Ctrl+K kereső, gyorsbillentyűk minden listán), és beépített AI-copilot segít az összefoglalásban és a következő lépés javaslatában.
Napi sales-munka
Kész, éles
A cégektől a lezárásig minden lépés egy rendszerben, dosszié-szemlélettel: egy cég oldalán látszik minden kontakt, esemény és nyitott deal.
Cégek & Kontaktok
Dosszié-nézet, szerep-flagek, dedup-ellenőrzés
Activity-timeline
Meeting / Hívás / Email / Jegyzet, forrás szerint (Bridge-jelzés is)
Pipeline
Kanban board, stage-history, elavulás-jelzés
Kampányok
Tölcsér-riport, CSV-import, konverzió-számítás
Teendők
Határidős lista, halasztás-fék
Kereső + AI-réteg
Kész, éles
A rendszer nem csak tárolja az adatot, hanem aktívan segít is vele dolgozni, kereséssel és AI-asszisztenssel.
Globális keresés
Ctrl+K, full-text search minden entitáson
Parancs-paletta
Gyors műveletek billentyűzetről
AI Copilot
Cég-összefoglaló, meeting-előkészítés, e-mail-javaslat, következő lépés
Zero-hallucination szabály
Minden AI-állítás forrás-ID-hoz kötött
Bridge-jelzés
Saját badge az activity-feedben, forrás-URL kötelező
Folyamat
Hogyan jut el egy jelzés a nodu-monitortól a SalesOS-ig
A nodu-monitor (a fenti közösség-figyelő scraper) nem közvetlenül ír a SalesOS adatbázisába — egy jól elhatárolt, auditálható folyamaton megy át minden jelzés:
1
A nodu-monitor észlel és pontoz
A Reddit-figyelés valós idejű (PRAW-stream), a többi forrást (Playwright, Stack Overflow, Google CSE) 90 percenkénti ciklusban járja körbe. Minden új bejegyzést a 25+ kulcsszavas listával pontoz (elsődleges kifejezés 3 pont, fájdalompont-jelző 2 pont, kontextus-szó 1 pont), és az eredményt — poszt-ID-vel, hogy ne duplikálódjon — a saját SQLite adatbázisába menti.
nodu-monitor
2
n8n továbbítja a SalesOS-nak
Az n8n-workflow rendszeresen lekérdezi a nodu-monitor SQLite-adatbázisát, és csak az 5 pontot elérő (Lead-küszöb) vagy magasabb jelzéseket veszi fel — az ez alatti posztok a Bridge oldalán maradnak, megfigyelésre. A kiválasztott jelzést a workflow a
POST /api/bridge/ingest
végponton adja át a SalesOS-nak, Bearer-kulcsos hitelesítéssel és egyedi
externalId
-vel, hogy egy jelzés véletlenül se kerüljön be duplán.
n8n
3
A SalesOS azonosítja a céget
Egyezés-keresés lépcsőzetesen fut: elsőként a cégjegyzékszám (Companies House-szám), majd az e-mail-domain a cég weboldalával, végül a normalizált cégnév pontos egyezése. Ha csak hasonló (de nem pontos) névre talál, a rendszer nem von össze automatikusan — új cég jön létre, és a jelzés emberi ellenőrzésre (⚠) kerül jelölve, hogy elkerülje a téves összevonást.
SalesOS
4
Deal vagy Activity, a pontszám szerint
7-es vagy magasabb pontszámnál a Deal a Qualified stage-ben nyílik, 5–6 pont esetén a Lead stage-ben. Ha a cégen már van nyitott deal, nem jön létre új: a jelzés csak Activityként kerül a meglévő dealhez, hogy elkerülje a duplikációt. Minden esetben a bejegyzés forrás-URL-lel és „Bridge" jelzéssel látható a cég dossziéjában.
SalesOS
5
Értesítés, és a sales kolléga átveszi
A #sales-leads Slack-csatornára automatikus értesítés megy ki az új jelzésről; onnantól a SalesOS felületén folytatódik a kézi munka — a dossziéban látja a kontextust, a pipeline-on léptetheti a dealt, a teendők közé felveheti a következő lépést. A tényleges kapcsolatfelvétel (Reddit-komment, LinkedIn-üzenet) mindig emberi jóváhagyás után megy ki — automatikus tömeges kiküldés tudatosan nincs.
Zoltán
Architektúra
Adatfolyam a scrapertől a NODU Salesig
Adatforrások
Reddit
r/Revit, r/ArchiCAD, r/BIM
Graphisoft Community
Playwright / Chromium
Autodesk Community
Playwright / Chromium
Stack Overflow
Stack Exchange API v2.3
Google CSE
RevitForum, BuildingSMART
Waitlist
nodu.build/bridge, egyenesen n8n-be
RB2B
Weboldal-látogató, ingyenes most
Feldolgozás
nodu-monitor
Kulcsszószűrő, 25+ kifejezés
Relevanciapontozás
primary 3pt · pain 2pt · context 1pt
SQLite adatbázis
Duplikátum-védelem
Claude Haiku
Válaszjavaslat-generálás
Slack-approve
👍/👎 gyorsjóváhagyás (P0, a Flask UI kiváltása)
Automatizáció
n8n → NODU Sales ingest
POST /api/bridge/ingest · Bearer-kulcs · idempotens
Company-match
házszám → email-domain → trigram → új cég
Deal
score ≥ 7: Qualified · 5–6: Lead · nyitott dealre csak Activity
Activity
forrás-URL kötelező · source = BRIDGE
Slack-értesítés
#sales-leads csatorna
Sales akció
Contacted
Reddit-komment / LinkedIn DM
Responded
Lead válaszolt
Demo / Onboarding
Bemutatkozás, bevezetés
Aktív felhasználó
Rendszeresen használja a Bridge-et
Automatikus és kézi lépések
A rendszer automatikusan gyűjt, pontoz és ment a NODU Salesbe (kötelező forrás-URL-lel, auditált ingest-naplóval). A kommunikáció (Reddit-komment, LinkedIn-üzenet) kizárólag emberi jóváhagyás után kerül ki — automatikus küldés tudatosan nincs (no mass outbound elv). Így a jelenlét hiteles marad, és megfelel a platformok feltételeinek.
Adatforrások részletesen
Melyik forrás, mit ad, mikor aktív
Forrás
Platform
Lekérdezés módja
Státusz
Korlát
Közösség-figyelés — nodu-monitor scraper
Reddit
r/Revit, r/ArchiCAD, r/BIM
PRAW API, valós idejű új posztok és kommentek
API-kulcs kell
Ingyenes tier
Graphisoft Community
community.graphisoft.com
Playwright Chromium, JS-alapú oldalak renderelése
Kész
90 perc/ciklus
Autodesk Community
forums.autodesk.com
Playwright Chromium, JS-alapú oldalak renderelése
Kész
90 perc/ciklus
Stack Overflow
stackoverflow.com, softwareengineering.SE
Stack Exchange API v2.3, tag és szöveges keresés
Kész
300 kérés/nap (API-kulcs nélkül)
Google Custom Search
RevitForum, BuildingSMART, egyéb
Google CSE JSON API, domain-szűrt keresés
API-kulcs kell
100 kérés/nap ingyenes
Weboldal — nodu.build/bridge
Waitlist
nodu.build/bridge
Waitlist-űrlap, egyenesen az n8n webhookra
Beillesztésre vár
Ingyenes, saját csatorna
RB2B ingyenes
nodu.build/bridge
JS snippet: anonim látogató-azonosítás, Slack-értesítés
Beillesztésre vár
USA, cégszint, csak Slack
RB2B Pro
nodu.build/bridge
JS snippet: személyszintű azonosítás, webhook (email-domain verify, no-PII)
2026 szeptember
Pro, automatikus NODU Sales
Implementáció
A megvalósítás fázisai
1
Meglévő alap élesítése
API-kulcsok bekonfigurálása a config.yaml-ban: Reddit (reddit.com/prefs/apps), Google CSE (console.cloud.google.com), céges Anthropic (Claude) API-kulcs — céges fiókkal, nem személyes kulccsal,
claude_enabled: true
—, Slack-webhook. Emellett a NODU Sales hosting/tunnel döntés (hogy az n8n elérje a lokális appot) és az adatbázis-mentés (pg_dump ütemezés) beállítása. End-to-end teszt: gyűlnek-e a posztok az SQLite-ba.
1–2 nap
Fejlesztő + Zoltán
2
Scraper connectorok
A Playwright (Graphisoft és Autodesk Community JS-oldalak) és a Stack Overflow connector kódja elkészült, a Reddit, a Google CSE és a HTML-fórumok mellett fut. Éles indításhoz még hátravan a Playwright-függőség telepítése a szerveren (
pip install playwright && playwright install chromium
).
Kód kész, telepítés: 2. sprint
Fejlesztő
3
n8n és NODU Sales integráció
A NODU Sales oldali ingest-adapter
elkészült
(POST /api/bridge/ingest — Bearer-kulcs, idempotencia, cég-match, stage-routing, audit-napló; spec: SalesOS docs/08). A fogadó rendszer azóta a teljes MVP-kört lezárta és élesben tesztelve fut: cégek/kontaktok, activity-timeline, teendők, pipeline-board, kampányok (a „Bridge Waitlist" kampány már most létezik és fogadja a jelzéseket), globális keresés és az AI-copilot mind működik, a kódbázis pedig verziózott és biztonsági mentése megvan. Hátravan: n8n-instance elindítása (cloud vagy self-hosted), a
BRIDGE_API_KEY
átadása neki, és a workflow átkötése erre az endpointra a Pipedrive helyett, plusz Slack-értesítés. Előfeltétel: az 1. fázisban eldöntött hosting/tunnel-megoldás élesben működjön.
1–2 nap
Fejlesztő
4
Waitlist oldal és feliratkozás
A nodu.build/bridge oldalon waitlist-űrlap (e-mail, név, szerepkör, fő fájdalompont) készül a NODU dizájnnal. A beküldés az n8n-en át a NODU Sales „Bridge Waitlist" kampányába érkezik (Registration lépcső) — a kampány-tölcsér automatikusan méri a konverziót. GDPR-megerősítés (double opt-in). Önálló, beágyazható komponens, amelyet a fejlesztő illeszt a weboldal stackjébe.
2–3 nap
Fejlesztő
5
RB2B látogató-azonosítás
Az RB2B ingyenes csomag snippetjét a fejlesztő illeszti be a /bridge oldalra; az anonim, USA-beli látogatókat cégszinten azonosítja, és jelez a Slacken. A teljes, automatikus NODU Sales-integráció (személyszint, webhook, email-domain-ellenőrzéssel és PII-védelemmel) a Pro csomaggal érkezik, az éles weboldali forgalom mellé, szeptemberben — a Pro-váltás költség-döntése Zoltáné, a technikai bekötés a fejlesztőé.
Most, Pro szept.
Fejlesztő + Zoltán
6
Hatékonyság-növelés
A fórumválasz-javaslatok finoman a waitlist-feliratkozásra terelnek, UTM-linkkel. Minden kimenő link UTM-címkét kap, így a NODU Salesben látszik, melyik csatorna konvertál; heti Slack-összefoglaló készül a forrásokról és a top fájdalompontokról. Emellett heti 1-2 LinkedIn-posztjavaslat érkezik a valós közösségi fájdalompontokból, jóváhagyásra.
2–3 nap
Fejlesztő
7
Slack-approve workflow (a Flask UI kiváltása)
A válaszjavaslat-jóváhagyás a Flask UI helyett Slack-first: 👍/👎 gyorsjóváhagyás a csatornában, egy kattintásos deep-review a teljes kontextussal, archiválás/halasztás. Ez a teljes konverzió-lánc szűk keresztmetszetét oldja fel.
Javasolt megvalósítás (fejlesztői feladat):
natív bővítés a meglévő Python-appban, nem n8n — az n8n egyirányú (Bridge → NODU Sales ingest), ez viszont kétirányú (Slack-kattintás → adatbázis-írás → visszajelzés Slackbe), és az app már úgyis beszél Slackkel és van saját adatbázisa. Konkrétan: (1)
notifier.py
bővítése Slack Block Kit gombokkal a draft-üzeneteken; (2) új Flask-route (pl.
/slack/actions
) a Slack-kattintás fogadására, aláírás-ellenőrzéssel; (3) egy DB-mező bővítés (
storage/db.py
) az approve/reject állapothoz. Előfeltétel: Zoltán létrehoz egy Slack App-ot a workspace-en (Bot Token + Signing Secret) — ezt csak workspace-admin teheti meg, a kódolás a fejlesztőé.
Megjegyzés: a korábban itt szereplő LinkedIn Apify-scraping a 2026-07-11-i audit alapján törölve — ütközik a „no LinkedIn scraping" elvvel. LinkedIn-jelenlét kizárólag kézi üzenetekkel és posztokkal.
2–3 nap
Fejlesztő
8
Relevancia-pontozás A/B teszt
A jelenlegi 3-2-1 kulcsszó-formula (elsődleges kifejezés 3 pont, fájdalompont-jelző 2 pont, kontextus-szó 1 pont) mellett egy LLM-alapú reclassification-ág tesztelése — melyik pontoz pontosabban. A relevancia-küszöbök (
BRIDGE_SCORE_QUALIFIED
,
BRIDGE_SCORE_LEAD
) env-konfigban hangolhatók, deploy nélkül. A tesztet a fejlesztő futtatja, az eredményt Zoltán értékeli.
3. sprint
Fejlesztő + Zoltán
Mit lehet azonnal indítani
A waitlist oldal és az RB2B ingyenes csomag nem vár a teljes weboldal élesedésére: amint a /bridge aloldal él, mindkettő gyűjthet. A scraper éles teszteléséhez az 1. fázis (API-kulcsok) szükséges; a kulcsok beszerzése és bekonfigurálása a fejlesztő feladata, a hosting/tunnel-döntés Zoltánnal közösen — a scraper kódja már kész.
Sales pipeline
NODU Sales: automatikus routing (stage-mapping)
A 2026-07-11-i architektúra-döntés szerint
a NODU Sales az egyetlen igazságforrás
— a Pipedrive kikerült a láncból („tiszta lap" döntés). A Bridge-jelzések a
POST /api/bridge/ingest
endpointon érkeznek (Bearer-kulcs,
externalId
-idempotencia, kötelező forrás-URL, auditált BridgeIngest-napló), és az alábbi szabályok szerint landolnak. A deal-pipeline a NODU Salesben:
Lead → Qualified → Meeting → Demo → Proposal → Won/Lost
— a belépő stage automatikus, minden további léptetés kézi, a boardon. A négytieres licencmodell struktúrája még kialakítás alatt van — a fejlesztés visszajelzéseitől és a leszállított funkcionalitástól függ (a jelenlegi állás a
Licencmodell
dokumentumban), a launch-kori ingyenes időszak feltételei egyelőre szintén nyitottak.
Bridge-jelzés
NODU Sales művelet
Belépő stage
Következő lépés
Scraper, score ≥ 7
Cég-match/létrehozás + Deal + Activity (forrás-URL-lel)
Qualified
Slack-értesítés; válaszjavaslat jóváhagyásra
Scraper, score 5–6
Cég-match/létrehozás + Deal + Activity
Lead
Slack-értesítés; megfigyelés, kézi minősítés
Scraper, nyitott deales cégen
Csak Activity a meglévő dealre — nincs duplikált deal
—
A jelzés a cég-dossziéban és az AI Briefben látszik
Waitlist-feliratkozó
Contact + „Bridge Waitlist" kampány-tagság + Activity; nincs auto-deal
Registration (kampány)
Köszönő e-mail; minősítés után kézi deal-nyitás
RB2B látogató
Company + Activity (látogatás-jelzés); nincs deal, nincs PII
—
Kézi mérlegelés; Pro-tól email-domain-verify
Minden jelzés
„Bridge" badge az Activity-feedben · a
painConfirmed
(MEDDIC) toggle-t a rendszer soha nem írja, az emberi döntés
—
Lead → … → Won/Lost léptetés kézzel, a boardon
Teendők
Következő lépések
Az alábbi sprint-beosztás javaslat, nem kötött határidő — nem biztos, hogy azonnal van rá fejlesztői kapacitás, a sorrend és az ütemezés a tényleges erőforrástól függően csúszhat.
Reddit API-kulcs bekonfigurálása (reddit.com/prefs/apps → script app létrehozása)
Fejlesztő
1. sprint
Google CSE API-kulcs és keresőmotor-azonosító beállítása (console.cloud.google.com)
Fejlesztő
1. sprint
Céges Anthropic (Claude) API-kulcs igénylése és bekötése — céges fiókkal, nem személyes kulccsal; a
claude_enabled: true
kapcsoló beállítása a config.yaml-ban
Fejlesztő
1. sprint
pip install playwright && playwright install chromium
futtatása
Fejlesztő
2. sprint
NODU Sales hosting/tunnel döntés (a lokális app elérhetővé tétele az n8n felől) + adatbázis-mentés (pg_dump ütemezés)
Zoltán + Fejlesztő
1. sprint
n8n-instance elindítása (cloud vagy self-hosted döntés); BRIDGE_API_KEY átadása az n8n-nek
Fejlesztő
2. sprint
n8n workflow átkötése a NODU Sales ingest-endpointra (POST /api/bridge/ingest) — a NODU Sales oldali adapter kész, tesztelve
Fejlesztő
2. sprint
Waitlist-oldal a nodu.build/bridge-en (waitlist-űrlap) és a "Waitlist → NODU Sales" n8n-workflow beállítása (channel: waitlist)
Fejlesztő
2. sprint
RB2B ingyenes csomag aktiválása és a JS snippet beillesztése a /bridge oldalra (Slack-értesítés)
Fejlesztő
2. sprint
Slack-approve workflow (7. fázis): 👍/👎 gyorsjóváhagyás a Flask UI kiváltására — a konverzió-lánc szűk keresztmetszete
Fejlesztő
3. sprint
Relevancia-pontozás A/B teszt (3-2-1 formula vs. LLM-reclassification); a küszöbök env-ben hangolhatók (BRIDGE_SCORE_QUALIFIED / BRIDGE_SCORE_LEAD) — Fejlesztő futtatja, Zoltán értékeli az eredményt
Fejlesztő + Zoltán
3. sprint
RB2B Pro előfizetésre váltás (költség-döntés), a technikai bekötés a fejlesztőé
Zoltán
2026 szept.
2026 sales cél összefoglalva
A rendszer célja, hogy 2026 végéig minél több lehetséges NODU Bridge-felhasználót érjünk el, majd az ingyenes időszak lejárta után, 2026. december 31-ig legalább 10 fizetős ügyfelet szerezzünk. Három belépő csatorna tölti folyamatosan a NODU Sales pipeline-ját: a közösség-figyelő scraper (Lead/Qualified deal), a waitlist-feliratkozás („Bridge Waitlist" kampány) és az RB2B látogató-azonosítás (cég-jelzés). A négytieres licencmodell struktúrája még kialakítás alatt van, a fejlesztés visszajelzéseitől és a leszállított funkcionalitástól függően alakul (jelenlegi állás:
Licencmodell
); a launch-kori ingyenes időszak feltételei egyelőre szintén nyitottak, a jelenlegi fókusz a felhasználószám növelése és az ingyenes feliratkozók fizetőssé konvertálása.
```

--------------------------------------------------

## FILE: nodu-bridge-license-calculator.html
Source: c:\NODU\NODU Bridge Repo\nodu-bridge-license-calculator.html
```
N
NODU Bridge
Licencmodell & Bevételkalkulátor
NODU Bridge Licencmodell
Parametrikus Archicad ↔ Revit konverzió saját mapping sablonokkal · Freemium → Professional → Studio → Enterprise (az Enterprise tier terv szerint 2027 elejétől) · Élő, inkrementális szinkron: Phase 3-ban érkezik (2026 Q4)
Licenctierek
2026-07-02 végleges irány: szerepkör + kapacitás tengely
A 2026-06-30-i Partnerhálózat-javaslatot (árazás aktív partner-kapcsolatok száma alapján) 2026-07-02-én elvetettük: az "aktív kapcsolat" önbevallással nem tartható fenn megbízhatóan, a telemetria-alapú kikényszerítés pedig irreális a mai desktop-plugin scope-ban. A Bridge launch-kori fő funkciója a
parametrikus Archicad↔Revit konverzió saját mapping sablonokkal
(script engine): a konverzió nem statikus geometriát, hanem parametrikus logikát visz át. Az élő, inkrementális szinkron a Phase 3-ban (2026 Q4) érkezik.
Helyette két, egymástól független,
lokálisan kikényszeríthető
tengely váltja fel: (1)
szerepkör-tengely
: Koordinátor (fizetős, sablon-alkotó) és User (ingyenes, de Koordinátor-számhoz kötött, limitált keretű), és (2)
kapacitás-tengely
: hány aktív projekt futhat egyidejűleg. Mindkettő a szoftver saját, amúgy is szükséges állapotából mérhető, nem igényel külön nyilvántartást vagy viselkedésmegfigyelést. A projektméret-limit ezektől elkülönülő, tisztán fair-use védelmi korlát marad.
Tier 0
Community
€0
/ hó
Egyéni próba · virális belépő
✓
Archicad ↔ Revit adatcsere
(batch konverzió, preset sablonokkal)
✓
Havonta 2 teljes modelles konverzió, elemszám-korlát nélkül
✓
3 mentett projekt
✓
30 napos projekt-előzmény
✕
Élő, inkrementális szinkron
(Phase 3, 2026 Q4)
✕
Saját sablon létrehozása/mentése
Koordinátor
✕
API hozzáférés
✕
Support (csak fórum)
Az adatcsere-alapélmény (teljes modell, korlátozás nélkül) itt is teljes értékű az eseti cserét futtató irodáknak (C réteg, 3–6 havonta egy IFC-átadás). A havi 2 konverzió a gyakoriság-alapú fair-use határ, nem az adatmennyiség; a fizetős határvonal tisztán funkcionális (script engine + saját sablon).
Tier 1 · Ajánlott
Professional
€199
/ Koordinátor / hó
€1,990 / Koordinátor / év (2 hó ingyen)
① Paywall · Script engine
✓
1 Koordinátor seat
Author
✓
10 ingyenes User seat
Contributor
✓
Parametrikus Archicad↔Revit konverzió
(logika-megőrző, nem statikus geometria)
✓
Script engine
(saját mapping sablon létrehozás/szerkesztés/mentés)
✓
Batch/egyszeri konverzió korlátlan számú futtatással
✕
Élő, inkrementális szinkron
(Phase 3-ban érkezik, 2026 Q4 – meglévő előfizetők automatikusan megkapják)
✓
2 egyidejűleg aktív projekt
✓
90 napos projekt-előzmény + alap analitika
✕
Közös sablonkönyvtár
✕
API hozzáférés
✓
E-mail support (48h SLA)
Projektméret: nagyvonalú fair-use korlát (a limit felett throttling, nem leállás): infrastruktúra-védelem, nem árazási csapda.
Tier 2
Studio
€499
/ iroda / hó
€4,990 / év
② Paywall · Iroda-folytonosság
✓
Minden Professional funkció
✓
2 Koordinátor seat
Author
✓
20 ingyenes User seat
Contributor
✓
5 egyidejűleg aktív projekt
✓
Közös sablonkönyvtár (Koordinátorok között megosztva)
✓
1 éves projekt-előzmény + teljes analitika
✓
REST API hozzáférés
✓
Alap audit napló
✓
Webhook integráció
✓
Google / Microsoft bejelentkezés (OAuth)
✕
SAML / Active Directory / Okta
✕
On-premise telepítés
✓
Priority support (24h SLA)
Projektméret: nagyvonalú fair-use korlát (throttling, nem leállás): infrastruktúra-védelem, nem árazási csapda.
Tier 3: jövőbeli tier, terv szerint 2027 elejétől
Enterprise
Egyedi
Min. €2,500 / hó · éves szerződés · induláskor nem indul, addig egyedi ajánlat
③ Paywall · Governance
✓
Minden Studio funkció
✓
5 Koordinátor seat
Author
(egyedi igény szerint bővíthető)
✓
50 ingyenes User seat
Contributor
✓
15 egyidejűleg aktív projekt
(bővíthető)
✓
Korlátlan projekt-előzmény + teljes analitika + iparági benchmark (opt-in)
✓
On-premise / dedikált felhő
✓
SAML SSO (Active Directory, Okta, SCIM)
✓
RBAC szerepkör-alapú jogok
✓
Teljes audit napló (ISO 27001)
✓
Platform Core hozzáférés (BIG graph + ERP integráció)
✓
Custom node fejlesztés
✓
Onboarding csomag (€2–8k)
✓
SLA + 24/7 mérnöki support
Projektméret: on-premise futtatás esetén a terhelés nem a NODU infrastruktúráján jelentkezik, ezért fair-use limit itt nem indokolt.
Eldöntve (2026-07-07): az élő szinkron Phase 3-ban érkezik, nem launch-funkció
A delta-only szinkron a Phase 3-ban marad (2026 nov – 2027 jan). A launch-kori értékajánlat a
parametrikus script engine + saját mapping sablonok
: a konverzió nem statikus geometriát, hanem parametrikus logikát (kapcsolatok, osztályozások, egyedi paraméterek) visz át – ez különbözteti meg az IFC-alapú munkafolyamatoktól. Az élő szinkron a meglévő Professional és Studio előfizetők számára automatikus frissítésként érkezik Phase 3-ban. A v1 konnektor elemtípusonként épül (falak kész, kivágások folyamatban, födémek és nyílászárók hátravannak); részletek:
Termék-roadmap
.
Paywall logika frissítési kiváltók
Community → Professional
A sablon mentési korlát + korlátozott konverziós keret
Az ügyfél elvégzi az első konverziót preset sablonnal, de nem hozhat létre/menthet saját mappinget (Koordinátor-jog hiánya), és havonta 2 konverziós kerete van. A következő projekten újra kellene felépítenie a leképezést. Ez az a fájdalompont, ami fizetővé tesz: a saját sablon idő-megtakarítás, a korlátlan konverzió pedig a napi munkafolyamat alapja.
"Szeretnéd menteni és újra felhasználni a mapping-sablonokat? Válts Professional-ra a korlátlan konverzióval."
Professional → Studio
Második Koordinátor · User-plafon · aktív projekt-limit
A Professional tier 1 Koordinátort, 10 ingyenes Usert és 2 egyidejűleg aktív projektet enged. Az upgrade három helyzetből fakad: (1) bejön egy második Koordinátor, (2) az iroda betölti a 10 fős User-keretet, (3) egyszerre 3. projektet is futtatni akarnak. A trigger konkrét, mérhető kapacitás-elérés, nem elvont csapatméret-becslés.
"2/2 aktív projekt betelt: új projekt indításához válts Studio-ra, vagy zárj le/archiválj egy meglévőt"
Studio → Enterprise
Adatszuverenitás · compliance
Nagyobb irodáknál az IT/legal tiltja a külső felhős adatátvitelt. Az SSO, az RBAC és az audit naplók nem a szoftver értékéről szólnak, hanem a vállalati infrastruktúra megfelelőségéről. Ez a paywall a tier megnyílásától (terv: 2027 eleje) él. Addig az ilyen igényű irodák egyedi ajánlatot kapnak.
"A projektek nem hagyhatják el a vállalati infrastruktúrát"
Enterprise → Platform Core
BIG graph + gyártás szinkron
A majdani Enterprise Bridge-előfizető hozzáfér a NODU platform alap-funkcióihoz, ahogy azok a Build-fázisokkal elérhetővé válnak. A mélyebb platform-integráció (BIG constraint optimizer, gyártástervező szinkron, ERP kapcsolat) adja majd a valódi 800h → 150h projektidő-csökkentést.
"Integráljuk a gyártástervező rendszerrel"
Bevételkalkulátor
Professional Koordinátorok száma
€199 / Koordinátor / hó  ·  a hozzájuk tartozó ingyenes User seat (10×) nem árazási tényező
Studio csapatok száma
€499 / iroda / hó  ·  2 Koordinátor + 20 ingyenes User seat
Enterprise szerződések száma
Jövőbeli tier, terv szerint 2027 elejétől · min. €2,500 / hó · induláskor 0 (egyedi ajánlatok)
Átlagos Enterprise érték (€/hó)
2.500
Min. €2,500 · Komplex deployment esetén €5–8k
Éves díjas ügyfelek aránya
60%
Éves előfizetők 2 hó kedvezménnyel javítja a cash flow-t
Havi Ismétlődő Bevétel (MRR)
€11.3k
Professional
Studio
Enterprise
Éves Ismétlődő Bevétel (ARR)
€0
MRR × 12 (alap)
Éves kedvezmény hatás
Nettó ARR
€0
0%
€200K ARR cél (2027) / €500K cél (2028)
Állítsd be az ügyfeleket a projekció megtekintéséhez.
Onboarding bevétel (egyszeri, éves becslés)
€0
Enterprise €3,500 átlag · Studio €500 setup fee
Lead-generációs realitás-becslés
Ez a blokk nem a költségekről szól, hanem arról, hogy a ténylegesen tervezett go-to-market csatornák (fizetett lead-gen rendszer, LinkedIn mikroinfluencerek, konferenciák) és egyetlen sales munkatárs kapacitása mellett havonta reálisan hány érdeklődő, illetve hány új fizető ügyfél várható. A konferencia- és influencer-hatás a valóságban hullámzó (esemény körüli csúcsokkal jelentkezik), itt az egyszerűség kedvéért havi átlagként szerepel.
Célpiac
Európa
Amerika (USA)
Ázsia
Az Archicad hazai piaca (Németország ~27%, 2021-es adat) miatt itt a legnagyobb a tényleges Archicad-Revit átfedés (~1 900–3 500 cég, belső becslés). Az Open BIM mandátumok (UK, DE, Nordics) nem kényszerítenek platformváltásra, hanem fenntartják a gyártófüggetlen leadási igényt: ez legitimálja és stabilizálja a vegyes-platformos piacot, nem önmagában hajtja azt.
Fizetett lead-gen rendszer
Havi büdzsé (€)
3.500
Költség / lead (CPL)
€200
Nincs AEC/BIM-specifikus publikált CPL-adat; a rokon B2B szegmensek (Construction ~210€, B2B SaaS ~175-220€, Software Dev ~550€) alapján €150–300 blended a védhető sáv. A korábbi €60–150 becslés a validáció során cáfolódott.
LinkedIn mikroinfluencerek
Influencerek száma
fő
Átlagos követőszám / fő
12.000
Posztok száma / hó / fő
4
Lead / 1000 elérés
0.10
Egybe vonja az organikus elérést, a kattintást és a kapcsolatfelvételt
Konferenciák
Konferenciák / év
db
Átlagos látogatószám / esemény
1.000
Releváns közönség aránya
12%
BIM-koordinátor / döntéshozó arány az általános AEC-közönségben
Lead-befogási arány
15%
Önkiszolgáló konverzió (Professional + Studio)
Lead → fizető ügyfél (önállóan, sales nélkül)
8%
A leadek túlnyomó része önállóan találja meg a Bridge-et és konvertál: nincs demó, nincs sales-kapacitás korlát. Az 5–8%-os Free→Paid benchmarkra épül (lásd a Kutatási alap szakaszt). A legjobb vertikális SaaS-benchmarkok plafonja is 5–6% körül van, a 8% már felső eset.
Enterprise sales-tölcsér (sales-asszisztált)
Enterprise-jelölt lead aránya
10%
A generált leadek hány százaléka minősül Enterprise-jelöltnek (nagy iroda, egyedi igény). Csak ez a szelet megy sales-asszisztált demó-tölcsérbe, a többi önállóan konvertál.
Sales munkatárs
fő
Kapacitás / fő (lead/hó)
40
Lead → demó arány
35%
Az Enterprise-jelölt leadek közül hány jut el a demóig (kvalifikációs ráta), nem a zárás
Demó → ügyfél arány
30%
Kizárólag az Enterprise-jelölt leadekre vonatkozik. Sales-asszisztált painkiller motion: a független benchmarkok forrásonként 15-70% között szórnak (a korábban idézett "35-55%, medián 55%" a legoptimistább forrásból származott, méghozzá hibásan hivatkozva); konzervatív, védhető sáv 30–45%, a 30% ennek alsó, óvatos bázisa. Lásd a Kutatási alap szakaszt.
Havi lead-bontás csatornánként
Lead-gen rendszer
–
LinkedIn influencerek
–
Konferenciák (havi átlag)
–
Összes generált lead / hó
–
Sales-kapacitás korlát
Tölcsér eredménye
Effektív Enterprise lead / hó
–
Új fizető ügyfél / hó
–
Ebből Professional
–
Ebből Studio
–
Ebből Enterprise
–
Önkiszolgáló ügyfelek megoszlása · Professional
Studio = maradék a 100%-ig. Az Enterprise itt nem szerepel: az a külön sales-tölcsérből érkezik.
12 hónap
24 hónap
36 hónap
Becsült összes új fizető ügyfél az időtávon
–
Realitás-ellenőrzés
Állítsd be a paramétereket az értékeléshez.
Kutatási alap és források
A fenti konverziós és piaci feltételezések 2024–2026-os független kutatáson alapulnak. A konverziónál a védhető, konzervatív sávvéget vettük: a painkiller-prémium hipotézis marad, amíg az első fizető kohorszok nem igazolják.
Az interoperabilitás kemény költsége:
15,8 Mrd USD/év
az USA-ban (
NIST GCR 04-867
, 2004-es tanulmány, 2002-es árakon, jelezve, hogy a szám elavult; frissebb, tágabb hatókörű becslés: az Autodesk-FMI 2021-es riportja 1,85 billió USD globális kárt említ "rossz adatból", ebből 88,7 Mrd USD rework); az újramunka a projektköltség
5–10%-a
az iparágban (konzervatív, a közvetett költségekkel együtt akár 10-25% is dokumentált).
Az IFC oda-vissza konverzió mindkét irányban elveszti a parametrikus adatot; a Revit→Archicad út hivatalos fórumon is
„fundamentally flawed"
, és nincs gyártói roadmap natív parametrikus átvitelre: a fájdalom valós, a megoldás kielégítetlen.
Sales-assisted painkiller motion konverziója forrásonként nagyon szór (
15–70%
): a GrowthSpree 55%-os mediánt közöl (sáv 35-70%), az ADV.me viszont csak 28-42%-ot mér, más források 15-30%-ot; a szórás a "sales-asszisztált" eltérő definícióiból fakad. Konzervatív, védhető tervezési sáv:
30–45%
(
ADV.me 2025
,
GrowthSpree 2026
).
A tényleges Archicad↔Revit átfedés Európában a legnagyobb (~1 900–3 500 cég), nem az USA-ban (~250–560): Archicad-natív piac és Open BIM mandátumok (
6sense
,
USP Research
,
ACE 2024
).
Kaveat: nincs publikus per-elem mérnökóra-szám kifejezetten az Archicad↔Revit esetre, és nincs nyilvános Revit/Archicad plugin-konverziós adat sem: a számaink modellezett, forrásolt becslések, nem hivatkozható tények.
Részletes piackutatás, módszertan és teljes forrásjegyzék →
Bevétel-előrejelzés (MRR-szimuláció)
A tervezés jelen szakaszában kizárólag a bevétel-oldal és a havi marketing büdzsé releváns, a csapat- és fix költségek egyelőre nem részei a modellnek. A szimuláció a fenti ügyfélszámokat veszi kiindulópontnak, és havi bontásban vetíti előre a bevétel (MRR) alakulását, figyelembe véve a marketingköltségből finanszírozott új ügyfélszerzést, az organikus növekedést, a lemorzsolódást (churn) és a Professional → Studio upgrade-mozgást (az egyszerűsített modell átlagosan 3 Professional Koordinátorból számol 1 Studio csapatot az upgrade pillanatában). A szimuláció 1. hónapja a GA hónapja (2026. szeptember), bevétel azonban csak a fizetés indulásától képződik: az addig felépülő bázis ingyenes felhasználókból áll.
Módosítás (2026-07-06): a bevétel-idővonal a fizetési rendszer érkezéséhez igazítva
A fejlesztői roadmap a fizetési rendszert a
nodu.bridge v2
-be sorolja, vagyis a szeptemberi GA-nál bevétel technikailag nem képződhet: a korábbi, GA-tól bevételt számoló idővonal ezt nem tükrözte. A szimuláció mostantól a "Fizetés indulása" csúszkával kezeli ezt: az addig tartó ingyenes időszak tudatos felhasználószerzési szakasz (ez a launch-stratégia része, nem kényszerű mellékhatás), a fizetés élesítésekor pedig az ingyenes bázisnak csak egy becsült része vált fizetőre. A fizetés korábbra hozása belső cél, de a tervezési alap a v2-es érkezés (2026. november); a csúszkával a korábbi vagy későbbi élesítés hatása is tesztelhető.
Konzervatív
Alap
Optimista
Alap szcenárió: mérsékelt növekedés, piaci átlag körüli churn és ügyfélszerzési költség (CAC).
Marketing büdzsé
Havi marketing büdzsé
Megoszlás: 60% Professional, 25% Studio, 15% Enterprise akvizíció (ez hajtja az új ügyfélszerzést a szcenárió CAC-értékein keresztül). Az Enterprise-rész a tier megnyílásáig arányosan a Professional/Studio csatornákra oszlik vissza.
Fizetés indulása (payment rendszer)
3. hó
A fejlesztői roadmap a fizetési rendszert a v2-be sorolja (terv: 2026. november = a szimuláció 3. hónapja). A GA-nál nincs számlázási képesség. Az indulási ingyenes időszak emellett tudatos felhasználószerzési szakasz. A korábbra hozás belső cél; a csúszkával tesztelhető a hatása.
Ingyenes bázis fizetővé válása
25%
A fizetés élesítésekor az addig felépült ingyenes felhasználói bázisnak csak egy része vált fizetőre. A 25% illusztratív kiindulóérték a self-serve trial→paid benchmarkok sávjából. Az ingyenes időszak lezárási feltételei (időtartam, landolási tier, grace-period) még nyitott döntések.
Enterprise tier megnyílása
5. hó
A szimuláció 1. hónapja 2026. szeptember (GA); az alapértelmezett 5. hónap 2027. január. A megnyílásig nincs Enterprise-akvizíció és Enterprise-bevétel. A dátum feltételezi, hogy a governance-képességek (SSO, on-premise) addigra leszállnak: ez fejlesztési függőség, amelyet a roadmap fejlesztői listája jelenleg nem támaszt alá (SSO/on-premise a v1–v4 tételek között nem szerepel). Enterprise-bevétel emellett legkorábban a fizetés indulásától képződhet.
Szimulációs időtáv
12 hónap
24 hónap
36 hónap
Havi bevétel (MRR) alakulása
Havi bevétel (MRR)
Első fizetős hónap MRR
–
Záró havi MRR
–
Kumulatív bevétel (időtáv alatt)
–
MRR-növekedési szorzó
–
Tier
LTV
CAC
LTV:CAC
Megtérülés
Professional
–
–
–
–
Studio
–
–
–
–
Enterprise
–
–
–
–
Realitás-ellenőrzés
Állítsd be a paramétereket az értékeléshez.
Feltételezések és piaci összehasonlítók
Paraméter
NODU Bridge
Speckle referencia
Megjegyzés
Free → Paid konverzió
5–8%
2–4%
Painkiller-pozíció + szűk vertikum a generikus 3-5% fölé emeli; a legjobb vertikális SaaS-benchmarkok plafonja is 5-6% körül van, a 8% felső eset, nem tervezési alap
Pro → Studio upgrade
15–20%
~10%
Második Koordinátor, User-plafon betelése, aktív projekt-limit elérése, API-igény
Studio → Enterprise
5–8%
3–5%
Compliance igény a nagyobb irodáknál
Átlagos user élettartam
8–12 év
–
A 8-12%-os éves churn matematikai következménye (1/churn): érett, lock-in utáni állapotot feltételez; az első 1-2 évben a korai kohorszoknál ennél magasabb churn valószínű, mielőtt a sablonkönyvtár + élő szinkron beágyazódik
Éves churn
8–12%
~15%
Célállapot AEC-beágyazottsággal (a piacon már bevezetett gyártóknál 1-5% is dokumentált); új belépőként a korai évekre optimista feltevés, kalibrálandó
Professional ARPU (éves)
€1,990–€2,388
–
Éves vs. havi mix alapján
Studio ARPU (iroda/év)
€4,990–€5,988
–
Fix irodai ár: 2 Koordinátor + 20 ingyenes User seat
Enterprise ARPU (éves)
€30k–€96k
€50k–€150k
Onboarding + éves licenc + custom fejlesztés
Szerepkör- és kapacitás-tengely: hogyan működik
A korábbi Partnerhálózat-javaslat (árazás aktív partner-kapcsolatok száma alapján) helyett két, egymástól független, a szoftver saját állapotából lokálisan kikényszeríthető tengely adja a licencelt kapacitást: nincs önbevallás, nincs külön telemetria-fejlesztés.
1. Szerepkör-tengely: Koordinátor vs. User
A
Koordinátor
(
Author
) hozza létre és módosítja a mapping/szinkron-sablont: ez a ritka, szakértői munka, ezért fizetős seat. A
User
(
Contributor
) egy meglévő sablont indíthat el egy új modellen (élő szinkronhoz vagy batch-konverzióhoz), de nem szerkesztheti a sablon logikáját: ez ingyenes, de a Koordinátor-számhoz kötött, rögzített kereten belül (1:10 arány a fizetős tierekben; a Community-ben nincs Koordinátor, így ott a szerepkör-megkülönböztetés nem értelmezett). Ez egy bináris jogosultság-ellenőrzés a licenckulcs szintjén, nem viselkedésmegfigyelés.
2. Kapacitás-tengely: aktív projektek száma.
A tier egy adott számú, egyidejűleg élő szinkronban lévő projektet enged. Egy projekt automatikusan inaktívvá válik (felszabadítva a helyet, a konfiguráció megmarad), ha 60 napig egyetlen modell-pár sem produkál szinkron-eseményt; a Koordinátor bármikor kifejezetten is archiválhatja. Limit-elérésnél kemény blokk: új aktív projekt csak hely felszabadulása vagy tier-váltás után indítható. Ez egy value-capture trigger, ezért szigorúbb, mint a projektméret fair-use throttlingja.
Tier
Koordinátor
User (ingyenes)
Aktív projekt
Community
0
nem értelmezett
nem értelmezett (nincs élő szinkron)
Professional
1
10
2
Studio
2
20
5
Enterprise
5
50
15
Miért nem a Partnerhálózat-modell, és mi maradt nyitva
2026-07-02: a Partnerhálózat-modellt (aktív adatcsere-kapcsolatok száma) elvetettük, mert az "aktív kapcsolat" fogalma önbevallással nem tartható fenn megbízhatóan, telemetria-alapú kikényszerítése pedig irreális a mai desktop-plugin scope-ban. A szerepkör- és kapacitás-tengely ugyanazt a célt szolgálja (árazás a tényleges használathoz kötve, miközben a teljes iroda hozzáférhet), de mindkettő a sync-motor saját, amúgy is szükséges állapotából mérhető.
Nyitva maradt, az első fizető ügyfelek adatai alapján kalibrálandó: a fenti táblázat számai (Koordinátor/User arány, aktív projekt-limitek) illusztratív kiindulópontok, nem véglegesek; a 60 napos dormancy-időablak szintén finomítható a tényleges projektritmus ismeretében. A projektméret-limit logikája (fair-use, throttling, nem value-capture) változatlan marad, és továbbra sem keveredik a fenti két tengellyel.
Nyitott döntési pontok
Döntő kérdés · Community → Professional határvonal
Pontosan miért fog fizetni az ügyfél?
A Community-ben az Archicad↔Revit adatcsere-alapélménynek teljes értékűnek kell lennie, enélkül nincs virális belépő. A jelenlegi munkahipotézis szerint a fizetős vonal az élő, inkrementális szinkron + a saját sablon létrehozása/mentése; a batch-konverzió preset sablonokkal ingyenes marad. Ez a határvonal azonban a pontos funkcionalitás ismerete nélkül (mit tud pontosan a preset sablon, hol kezdődik a "saját" mapping) nem zárható le: a fejlesztéssel együtt kell véglegesíteni. Ez a licencmodell legfontosabb nyitott kérdése.
Free tier kalibrálás (LEZÁRVA 2026-07-06)
Havonta 2 teljes modelles konverzió, elemszám-korlát helyett
A korábbi 500 elemes korlátot a 2026-07-06-i szakértői felülvizsgálat nagyságrenddel alacsonynak találta: egy tipikus közepes Archicad épületmodell 30 000–150 000+ elem, tehát az 500 elem valójában részmodell-demó volt, nem "pilot homlokzati projekt". Az új szabály gyakoriság-alapú: teljes modell, elemszám-korlát nélkül, havonta 2 alkalommal. Ez pontosan a C réteg (3–6 havonta egy IFC-átadás, fájdalom-intenzitás szerinti rétegzés) számára ad teljes értékű, ingyenes kiszolgálást, így a Community tier végre betölti deklarált szerepét (valódi érték, virális belépő), miközben aki gyakrabban cserélne, az definíció szerint a B/A rétegbe, tehát a fizetős tierekbe tartozik. A differenciátor (saját sablon, élő szinkron) változatlanul fizetős marad.
Professional ár
€99 vs. €199 / Koordinátor / hó
A €99 gyorsabb free-paid konverziót hozna, a €199 viszont komolyabb szűrőként működne. Az AEC piacon az alacsony ár olykor gyanút kelt. Javasolt: €199 - magabiztosabb pozicionálás, magasabb LTV. Az indulási termékkör (élő, inkrementális szinkron + sablon-alapú konverzió) értékajánlatához ez az ár illik; a végleges kalibrálás az első 50 fizető ügyfél konverziós adatai alapján dönthető el.
Studio trigger
Második Koordinátor, User-plafon vagy aktív projekt-limit, nem csapatméret
Az upgrade konkrét, mérhető kapacitás-eléréskor jön: második Koordinátor kell, betelik a 10 fős ingyenes User-keret, vagy egyszerre 3. projektet akarnak élő szinkronban futtatni a Professional 2-es limitje felett. Javasolt: mindhárom eseményre célzott in-app üzenet, nem elvont csapatméret-becslés.
Enterprise floor
€2,500 / hó minimum, a tier megnyílásától
Az Enterprise tier induláskor nem indul: tartalmi elemei (SSO, on-premise, Platform Core) nem v1-képességek. A floor a tier megnyílásakor (terv: 2027 eleje) lép életbe; addig a nagy irodák egyedi ajánlatot kapnak. Konzervatív ár: bevezetési díjjal az éves bevétel €32–46k, ha pedig BIG graph integráció is benne van, akkor €4–5k/hó reálisabb. Javasolt: €2,500 mint floor, felfelé egyedi tárgyalás.
User/Koordinátor arány kalibrálás
1:10 arány, illusztratív kiindulópont
A rögzített 1 Koordinátor : 10 User arány (és a tierenkénti 1/2/5 Koordinátor, 2/5/15 aktív projekt szám) egyelőre becslés, nem az első ügyfelek tényleges használati adatából származik. Javasolt: az első 50 fizető ügyfél tényleges User-kihasználtsága és projekt-egyidejűsége alapján felülvizsgálni, mielőtt a limitek kemény blokkot váltanának ki a gyakorlatban.
Dormancy-időablak kalibrálás
60 nap, óvatos alapérték
A 60 napos inaktivitási időzítő (ami után egy projekt automatikusan felszabadítja a helyét az aktív projekt-limitben) szándékosan hosszú, hogy elkerülje a hamis-pozitív kizárást (aktív projekt téves inaktívvá minősítése egy csendesebb projektfázisban). Javasolt: a tényleges AEC-projektritmus ismeretében rövidíthető, ha az adat azt mutatja, hogy a limitek emiatt ritkán telnek be reálisan.
NODU Bridge Licencmodell v1.5  ·  2026-07-06  ·  Belső tervezési dokumentum  ·  poczai@nodu.build
```

--------------------------------------------------

## FILE: nodu-bridge-piac-elemzes.html
Source: c:\NODU\NODU Bridge Repo\nodu-bridge-piac-elemzes.html
```
Belső stratégiai dokumentum
Piaci igényelemzés az Archicad–Revit kollaborációs rés mérete és értéke
Fókusz: folyamatos, projektszintű együttműködés nem egyszeri migráció · Európa + USA
Módszertan és korlátok
Ez a dokumentum nyilvánosan elérhető iparági adatokból, piaci intelligencia adatbázisokból (Enlyft, 6sense), szakmai szervezetek felméréseiből (ACE 2024, AIA 2024) és Autodesk listaáraiból konstruált becslésláncot tartalmaz. A Graphisoft nem hozza nyilvánosságra az aktív licencek számát; Archicad-specifikus felhasználói adatok nem ellenőrizhetők külső forrásból. A becsléslánc minden lépésénél feltüntetjük a bizonytalanság szintjét. A számok irányt mutatnak, nem pénzügyi előrejelzések.
    Egy másik, kifejezetten a bevételkalkulátor konverziós és régiós feltételezéseihez készült, kattintható forrásokkal ellátott bizonyíték-napló elérhető a
Piackutatás
dokumentumban.
00 Célfelhasználó
A valódi célfelhasználó: a BIM koordinátor
Nem a teljes iroda a célfelhasználó. Egy 10–15 fős Archicad-es irodában jellemzően 0–1, ritkábban 2 BIM koordinátor az, aki ténylegesen kezeli az adatcserét: a szerep kisebb irodáknál gyakran hibrid (egy tervező viszi mellékfeladatként). Ő szervezi az IFC-exportot, ő tartja a kapcsolatot a Revit-es partnerrel, és ő érti a konverzió fájdalmát.
Az átlagos tervező a saját szoftverében dolgozik, és nem foglalkozik adatátvitellel. Ez a különbség alapvetően meghatározza, hogyan kell gondolkodni a NODU Bridge piacáról.
Három következménye van ennek:
Kit kell elérni.
Nem az irodavezetőt kell meggyőzni elsőként, hanem a BIM koordinátort. Ő a szakmai közösségekben aktív: Graphisoft-fórumokon, AEC LinkedIn-csoportokban, BIM koordinátori Slack-csatornákon. Ha ő megtapasztalja az értéket, ő mutatja meg a principálnak. Fontos szereposztás: a koordinátor a champion (ő választja ki és validálja az eszközt), de 10–50 fős irodánál a szerződést tipikusan a principál/ügyvezető írja alá: az önkiszolgáló tölcsérnek a koordinátort kell megfognia, az árazásnak/ROI-érvnek a principálhoz kell szólnia.
Hogyan kell árazni.
Irodánként nem 10–15 fizetős licencről van szó, hanem 1–2 Koordinátorról, akik létrehozzák és karbantartják a mapping- és szinkronsablonokat, és csak az ő seatjük fizetős. Az iroda többi tagja ingyenes User seatet kap (a Koordinátor-számhoz kötött keretben), így az élő szinkron a teljes irodát eléri, miközben a fizetendő összeg a szakértői munkát követi, nem a létszámot. Ez kedvező a belépési küszöb szempontjából.
Mi az értékesítési út.
A BIM koordinátor a beachhead. Ő vezeti be az eszközt, ő dokumentálja az időmegtakarítást, és ő viszi az irodát a Professional-ról a Studio tierre. Hosszú távon (a platform-fázis megnyílásával) ugyanez az út vezet tovább az Enterprise tier és a NODU platform-ökoszisztéma felé.
Egy lehetséges második profil: jövőbeli irány
Az induláskor a célfelhasználó egységesen a BIM koordinátor: az adatcserét végző szakember. A platform későbbi, VSE-alapú parametrikus tartalom-készítési képessége egyszer megnyithat egy második profilt: a parametrikus tartalom-alkotót, aki nem meglévő Archicad modellt konvertál, hanem új parametrikus tartalmat hoz létre, amely a 2026-07-06-i pontosítás szerint többformátumú kimenetre készül: Revit Family mellett további CAD- és gyártói formátumokra is. Ez a profil nem része az indulási termékkörnek, és az alábbi piaci számítások nem kalkulálnak vele. Szándékosan nyitva hagyott, későbbi kérdés.
A gyártói szegmens mint önálló piac: kidolgozott blueprint, jövőbeli irány
A gyártói szegmensre 2026-06-11 óta önálló, döntés-előkészítő anyag létezik: a
NODU Creator (Content Engine) blueprint v2.0
. Ennek lényege, hogy a gyártói tartalom-előállítás nem „Revit Family generátor", hanem knowledge-graph-alapú termékadat-motor, amelyből a Revit Family csak egy a sok export közül (IFC, Archicad, SketchUp, COBie, carbon/DPP, cost); a védhető eszköz a termék-tudásgráf, nem a formátum-szám. A blueprint saját piacszámokkal dolgozik (niche-TAM ~0,3–2 Mrd USD; EU SAM ~1 500–3 500 számla; 3 éves SOM 20–50 fizető ügyfél, ~€400–600k ARR), saját árazással (Starter/Growth/Enterprise, €3–50k/év) és sales-vezérelt, pilot-alapú GTM-mel, vagyis termékvonal-szintű B2B-üzlet, alapvetően eltérő logikával, mint a Bridge iroda-szintű, önkiszolgáló modellje. A vezetőség az irányt támogatja, a részletes kidolgozás későbbre ütemezett; elképzelhető önálló termékként is, miközben a generálási mag a Bridge-platformon is jelen lenne. A fenti Bridge-piacméret-becslések ezt a szegmenst változatlanul nem tartalmazzák.
01 A piac szerkezete
Két szoftvervilág, amelyek ugyanazon az építési projekten találkoznak
A NODU Bridge releváns piaca nem az Archicad-felhasználók összessége, és nem is a Revit-felhasználóké. A releváns piac ott keletkezik, ahol egy Archicad-es építész iroda és egy Revit-es mérnöki partner (szerkezet, MEP, generálkivitelező) ugyanazon a projekten dolgozik heteken vagy hónapokon át, párhuzamosan.
Ez a helyzet Európában strukturális, nem kivételes. A multidiszciplináris AEC-projektek természetéből adódik, hogy az építész és a mérnöki szakterületek más-más szoftverkörnyezetből dolgoznak. Az európai piacon az Archicad és a Revit egyaránt jelen van, de az infrastruktúra, a mérnöki dokumentáció és a kivitelezés egyre inkább Revit-centrikus. Az eredmény: az Archicad-es iroda állandó adatcsere-kényszert él meg, amelyet ma kizárólag IFC-exporttal oldhat meg, összes dokumentált hátrányával együtt.
Szoftver-penetráció regionálisan
Régió
Revit részesedés (BIM)
Archicad részesedés (BIM)
Archicad trend
Megjegyzés
Európa (átlag)
~45%
~33%
Stabil
USP Research felmérés, 2024
Németország
~30–35%
~27–30%
Stabil
Nemetschek csoport is jelen; háromirányú verseny
UK
~27% (2020) → ~49% (2026 proj.)
~15–20%
Csökken
Erős kormányzati BIM-mandátum hajtja Revit felé
DACH (AT, CH)
~35–40%
~30–35%
Stabil
Graphisoft erős hagyományos jelenléte
Kelet-Közép-Európa
~40–50%
~25–35%
Stabil–enyhe csökk.
Archicad erős magyar, cseh, lengyel piacon
USA
~63.5%
~7–10%
Gyenge
Revit de facto standard; AIA 2024 felmérés
Ausztrália
~40–45%
~25–30%
Stabil
Archicad erős jelenlét, design-fókuszú piac
Források: USP Research European BIM Survey, AIA 2024 Firm Survey, bimheroes.com Revit migration analysis, Graphisoft Community adatok.
Az adatokból kiolvasható alaphelyzet: Európában az Archicad-es irodák döntő többsége Revit-es partnerekkel dolgozik nemcsak alkalmanként, hanem rendszeresen. Az USA-ban az Archicad-es irodák szinte minden projekten Revit-es környezetbe ütköznek, hiszen az ökoszisztémájuk 63,5%-a Revitre épül.
02 Felhasználóbázis-becslés
Hány iroda él meg aktívan Archicad–Revit kollaborációs súrlódást?
A célpiac méretét nem lehet közvetlenül mérni: nincs nyilvánosan elérhető adat arról, hogy hány Archicad-es iroda dolgozik rendszeresen Revit-es partnerekkel. A becslés szűrési láncon keresztül közelíthető meg. Minden szűrőnél megadjuk a bizonytalanság szintjét.
Európa
Szűrési lépés
Arány
Becsült szám
Bizonytalanság
Regisztrált építészek Európában
–
580 000 fő
Alacsony: ACE 2024 Sector Study
Archicad BIM-felhasználók (~33%)
33%
~191 000 fő
Közepes felmérési adatból
Aktív építész irodák száma (tipikusan 1–20 fős)
–
60 000–100 000 iroda
Közepes becslés az átl. irodaméretből
Archicad-es irodák (~33%)
33%
20 000–33 000 iroda
Közepes
5+ főre tervező, multidiszciplináris projekteket kezelő irodák
~35–40%
7 000–13 000 iroda
Közepes–magas
Rendszeresen Revit-es partnerekkel dolgozó irodák
~55–65%
4 000–8 500 iroda
Magas: nincs direkt adat
Parametrikus workflow-érettség, tool-vásárlási hajlandóság
~20–30%
800–2 500 iroda
Magas: korai befogadói szűrő
USA
Az USA az Archicad szempontjából másodlagos, de stratégiailag érdekes piac. Az AIA 2024 felmérés szerint több mint 19 000 építész iroda működik az USA-ban, és ezek 75%-ának 10 főnél kevesebb alkalmazottja van. A Revit dominanciája (~63,5%) miatt az Archicad-es irodák különösen intenzív kollaborációs súrlódást tapasztalnak, hiszen partnereik szinte mindegyike Revit-en dolgozik.
Szűrési lépés
Arány
Becsült szám
Bizonytalanság
Regisztrált építész irodák az USA-ban
–
>19 000 iroda
Alacsony: AIA 2024
Archicad-et használó irodák (~7–10%)
7–10%
1 330–1 900 iroda
Közepes (piaci becslés)
5+ fős, multidiszciplináris projekteket kezelő irodák
35–45%
465–855 iroda
Közepes
Rendszeresen Revit-es partnerekkel dolgozó irodák
~75–85%
350–725 iroda
Alacsony: Revit dominancia miatt szinte biztos
Parametrikus workflow-érettség, tool-vásárlási hajlandóság
~25–35%
90–255 iroda
Magas (belső becslés)
Globális összesítés
Archicad-es irodák globálisan
25 000–45 000
Európa + USA + Ausztrália + egyéb
Aktív Revit-kollaborációs igény
5 000–10 000
Szűrt: méret, projekt-komplexitás, partner-struktúra
Konzervatív SAM-mag (tervezési alap)
900–2 800
Parametrikus érettség + vásárlási hajlandóság szűrővel; a bevétel-tervezés erre a számra épül
Enlyft detektált cégek (alulbecsült)
7 227
Digitálisan felismerhető nagyvállalatok; KKV-k nincsenek benne
A legkritikusabb bizonytalanság és hogyan kezeljük
A szűrési lánc leggyengébb láncszeme az „aktívan Revit-es partnerrel dolgozó" szűrő. Nincs iparági felmérés arról, hogy az európai Archicad-es irodák hány százaléka tapasztal heti rendszerességű Revit-kollaborációs súrlódást azokkal szemben, ahol a csere 3–6 havonta egyszeri IFC-átadással megoldható. Ez a különbség akár 3–4-szeres tényezőként befolyásolja a valós SAM-ot. A 05. szekció ezért erre a tengelyre építi a SAM szerkezetét: az állomány fájdalom-intenzitás szerinti A/B/C rétegzése ezt a bizonytalanságot explicit, design partnerrel validálható rétegarányokká alakítja.
03 Ár-pozicionálási kontextus
Mihez méri az iroda a Bridge árát
Fontos tisztázás: a NODU Bridge
nem váltja ki
sem az Archicadot, sem a Revitet: mindkét fél a saját szerzői eszközében dolgozik tovább, a Bridge a kettő közötti adatáramlást oldja meg. Az iroda teljes Autodesk- vagy Graphisoft-költése ezért nem viszonyítási alap: az a Bridge-dzsel együtt is változatlanul megmarad. A Bridge árát a vásárló két dologhoz méri: (1) mennyit költ ma hasonló
kategóriájú
eszközökre (interop, modell-QA, koordináció), és (2) mennyi munkaórát takarít meg vele: ez utóbbi a valódi érték-horgony, amelyet a 04. szekció számszerűsít.
Szerzői szoftverek listaárai kontextusként (2025–2026)
Az alábbi árak nem a Bridge alternatívái, hanem a vásárló költségvetési környezetét mutatják: ekkora tételek mellett kell elférnie egy interop-eszköznek.
Termék
Éves ár / fő (USD)
Éves ár / fő (EUR, ~0.92)
Megjegyzés
Revit standalone
$3 005
~€2 764
Csak Revit; évi ~3% áremelés 2024–2026 között
AEC Collection
$3 115–$3 200
~€2 866–€2 944
Revit + Civil3D + Navisworks + további eszközök
Archicad (Studio / Collaborate)
$2 414–$2 840
~€2 220–€2 615
2024–2025-ben a perpetual licenc kivezetve, csak előfizetés
Revit Flex (eseti use)
$30 / nap
~€27 / nap
Alkalmi Revit-hozzáférés token-alapon; a kereslete jelzi, hogy létezik a „Revit csak interopra" minta
Forrás: gyártói listaárak, 2025–2026. Vállalati tárgyalással 15–35% kedvezmény elérhető. Európai árak helyi adókkal + viszonteladói felárral magasabbak lehetnek.
Egy szűk kivétel: a defenzív Revit-seat
Egyetlen esetben vált ki a Bridge tényleges szoftverköltséget: ha egy Archicad-alapú iroda ma
kizárólag az adatcsere és a beérkező modellek ellenőrzése miatt
tart fenn 2–3 Revit-licencet, vagy Flex-tokeneket vásárol erre a célra. Ez a defenzív költés $6 000–$9 600/év szoftverkiadást jelent úgy, hogy a parametrikus adatmegőrzés problémáját nem oldja meg. Ez az érv azonban
feltételes mellékérv, nem általános horgony
: csak azokra az irodákra érvényes, amelyek ma ténylegesen így dolgoznak: hogy ez a célszegmens mekkora hányada, arra nincs adatunk, az első ügyfélinterjúkból derül ki. Az Autodesk Flex termék létezése és kereslete közvetett bizonyíték arra, hogy a minta létezik.
A valódi érték-horgony: a megspórolt munkaóra
A Bridge nem szoftvert vált ki, hanem munkaidőt: az IFC-alapú csere export-import-javítás ciklusait és az újramodellezést. Ennek számszerűsítése (€7 800–17 300/projekt/év, saját, iparági idő- és béradatokból levezetett becslés) a 04. szekcióban található; a bevételi és ROI-érvelésnek erre kell épülnie, nem szoftverhelyettesítésre. Az árszint-elhelyezéshez (mennyibe kerülnek a hasonló kategóriájú eszközök) a lenti tábla ad kontextust.
A komparábilis eszközkategória: interop, modell-QA, koordináció
A Bridge árának valódi viszonyítási kategóriája nem a szerzői szoftver, hanem az az eszközréteg, amelyet az irodák ma az adatcsere és a modellminőség kezelésére vásárolnak. A €199/Koordinátor/hó Professional pozíció ebben a kategóriában a commodity BCF/issue-eszközök felett, a prémium modell-ellenőrző eszközök sávjában helyezkedik el - miközben olyan képességet ad (élő, parametrikus-megőrző szinkron), amelyet ma egyik kategóriatag sem kínál.
Eszköz
Kategória
Éves ár
BIMcollab (CDE Enterprise)
BCF issue-koordináció
~€300–470 / fő (25–39 €/fő/hó)
Speckle Team (teljes workspace, nem per fő)
Open BIM adatcsere
~$1 188 (99 USD/hó)
Solibri (Advanced–Premium tier)
BIM minőségbiztosítás / IFC
~€2 109–2 772
NODU Bridge Professional
Élő Archicad↔Revit szinkron
€1 788 (149 €/Koordinátor/hó) · éves díjjal €1 490
NODU Bridge Studio
Iroda-licenc: 2 Koordinátor, közös sablonkönyvtár, API
€5 988 (499 €/iroda/hó) · éves díjjal €4 990
NODU Bridge Enterprise (jövőbeli tier, induláskor egyedi ajánlat)
On-premise / SSO / platform-hozzáférés (a platform-fázissal nyílik meg)
Egyedi; a tier megnyílásakor min. €30 000 (2 500 €/hó floor)
Forrás: gyártói listaárak, 2025–2026; részletes forrásjegyzék a
Piackutatás
dokumentumban. Megjegyzés: a Solibri 2026-ban a korábbi „Office/Site" terméknevekről tier-struktúrára (Starter/Essential/Advanced/Premium/Security+) állt át: a fenti sor a mai Advanced-Premium tiernek felel meg. Közvetlen, élő Archicad↔Revit szinkronra publikus árazású versenytárs nincs: a Bridge egy új kategóriát képvisel, a fenti sáv csak a költségvetési elhelyezést segíti.
04 Az interop-fájdalom rejtett ára
Az IFC-alapú csere valódi idő- és munkaköltségei
Az IFC-alapú adatcsere nem „ingyenes": az iroda ezt munkaórában fizeti meg. Az alábbi kalkuláció konzervatív becslés. A valóság rosszabb lehet, ha az importált IFC-fájl javítása is szükséges Revitben, vagy ha a geometriai degradáció később jelentkező hibákat okoz a tervdokumentációban.
A fájdalom nemcsak fórum-beszámolókból, hanem nemzeti szintű, módszertanilag dokumentált kutatásból is alátámasztható: a
NIST GCR 04-867
tanulmány évi 15,8 milliárd USD interoperabilitási veszteséget dokumentál az USA építőiparában. Ez a szám nem az Archicad–Revit esetre specifikus, de megerősíti, hogy az alábbi irodaszintű kalkuláció nagyságrendje reális.
Tevékenység
Dokumentált idő
Forrás
IFC export Archicadből (komplex modell)
3–4 óra (gyakran egyik napról a másikra átnyúlva)
Autodesk Community, Graphisoft Community fórumok
IFC import és ellenőrzés Revitben
4–6 óra
Dokumentált felhasználói tapasztalat
Hiányzó geometria és triangulált felületek javítása
1–3 óra / importálás
Graphisoft IFC hibaelhárítási útmutató
Elveszett parametrikus kapcsolatok újraépítése Revitben
Projektfüggő: 0-tól több napig
Csak komplex modelleknél releváns
Éves munkaidő-veszteség példakalkuláció
Egy aktív projekt, heti 1 IFC csere, 6 hónapos aktív tervezési fázis
Cserék száma
~24 alkalom / év
Idő / csere (export + import + ellenőrzés)
~5–8 óra
Éves időráfordítás (konzervatív)
~120–192 óra
Becsült óraköltség (senior BIM koordinátor)
€65–90 / óra
Éves rejtett IFC-teher (1 projekt)
€7 800–€17 280
IFC-teher vs. Bridge-licenc éves összevetés
Bridge Professional / év
€1 788
Bridge Studio / iroda / év
€4 990–5 988
IFC-teher / projekt / év
€7 800–17 280
IFC-teher / iroda / év
(3 aktív projekt)
€15 000–35 000
A sávok arányosak (€0–35 000 skála); a világosabb szakasz a becslési sáv felső részét jelöli. Az IFC-teher konzervatív becsléssel is a Studio-licenc többszöröse: a Bridge ára a megspórolt munkaidő töredéke.
ROI-kalkuláció összefoglalója
Egy 10 fős Archicad-es iroda, amely 2–3 aktív multidiszciplináris projektet kezel egyidejűleg, évente becsülhetően
€15 000–€35 000
értékű munkaidőt fordít IFC-alapú adatcserére és utómunkára, a rejtett hibajavítási és tervdokumentációs eltérésekből eredő további költségek nélkül. Ez az a rejtett ár, amellyel a NODU Bridge Studio tier (€499/hó = €5 988/év) közvetlenül versenyez: a licencdíj a konzervatívan becsült teher 17–40%-a, a megtakarítás már az alsó sávban is többszörösen fedezi az árat.
€7 800+
Éves IFC-teher / projekt (konzervatív)
€30 000+
Éves IFC-teher / iroda (3 aktív projekt)
<1 év
Becsült megtérülési idő (Studio tier)
Figyelmeztetés a kalkulációhoz
Az IFC-teher számítása a legkonzervatívabb forgatókönyvet veszi alapul: tapasztalt BIM koordinátor, aki ismeri a folyamatot. Valóságban a tanulási görbe, az ad hoc hibák és a később jelentkező tervdokumentációs eltérések ennél jóval magasabb tényleges költséget eredményeznek. Másrészről kisebb, egyszerűbb projekteken, ahol az IFC-csere havi egyszeri esemény, ez a szám drasztikusan csökken. A fenti becslés komplex, 12+ hónapos projektekre vonatkozik.
A Platform mint jövőbeli végpont
A fenti ROI tisztán a Bridge önálló értékén (a megspórolt IFC-munkaidőn) alapul; platform-értéket nem tartalmaz. Hosszú távon a Bridge a NODU platform belépési kapuja: a Build-fázisok koordinációs, verziókezelési és adatszinkronizációs funkciói a majdani Enterprise tier részeként ezen felül további értéket adnak. Ez a számításokban tudatosan nem szerepel: minden platform-érték felfelé mutató tartalék.
05 Piaci méret (TAM / SAM / SOM)
A piac mérete három horizonton
A TAM/SAM/SOM keretrendszert itt a szokásosnál óvatosabban kell értelmezni. Az input adatok bizonytalanok, és a piaci érettség (vagyis hogy mennyi iroda hajlandó fizetni dedikált interop-eszközért) empirikusan nem mért. Az alábbi számok a rendelkezésre álló adatokból konstruált becslések, nem független piaci elemzők validált előrejelzései.
A becsült bevétel/iroda tudatosan emelkedik TAM→SAM→SOM felé (€3 500 → €4 500 → €5 000): minden szűkítési lépés nemcsak a darabszámot csökkenti, hanem egyre jobb illeszkedésű irodákra szűr (aktívabb fájdalom, meglévő vásárlási hajlandóság, végül ténylegesen megnyert ügyfél), ami magasabb átlagos ügyfélértéket valószínűsít. A lenti fájdalom-intenzitás rétegzés ezt a progressziót levezethetővé teszi: a rétegek természetes tier-besorolása (A→Studio €5 988/év, B→Professional €1 788/év) adja az átlagérték szerkezeti alapját, a konkrét súlyozás azonban továbbra is belső feltevés, nem mért adat.
TAM · 12 000–20 000 iroda
€42M–€70M/év bevételi potenciál
Fizetőképes fájdalmú piac · 1 600–4 700 iroda
A réteg + B réteg fele · intenzitás-alapú, belső becslés
SAM-mag · 900–2 800 iroda
tervezési alap · ~55–60% realizmus-diszkonttal
SOM · 90–400 iroda
€200K (2027) → €500K (2028) → ~€800–1.2M (2029)
C réteg
1 500–5 000 iroda
eseti IFC-csere
nem SAM:
Community-bázis,
hosszú távú
konverziós tartály
A sávszélességek illusztratívak (logaritmikus arányúak); a valódi szűkülés ennél meredekebb: a SOM a TAM ~2%-a. A C réteg (szaggatott keret) nem része a tölcsérnek: az eseti cserével dolgozó irodák az ingyenes Community tier célközönsége.
TAM Teljes elérhető piac
12 000–20 000 iroda
Minden Archicad-es iroda globálisan, amelynek rendszeres Revit-es projektpartnere van. Bevételi potenciál:
€42M–€70M/év
(avg. €3 500/iroda/év). Belső becslés, független forrás nem támasztja alá közvetlenül.
SAM Kiszolgálható piac
900–2 800 iroda
Konzervatív mag, fájdalom-intenzitás alapon rétegezve (lásd a lenti rétegzési táblát): a folyamatos együttműködésű A réteg és a szakaszos B réteg fele adja a fizetőképes fájdalmú piacot (~1 600–4 700 iroda), amelyből a tervezési alap a validálatlan konverziós realizmus miatt ~55–60%-os diszkonttal képződik. A tágabb, „aktív mixed-tool átfedés" definícióval mért sáv (~1 400–3 600 iroda, lenti regionális tábla) független módszertanként ugyanebbe a nagyságrendbe fut. Bevételi potenciál a konzervatív magra:
€4M–€12,6M/év
(avg. €4 500/iroda/év).
SOM 3 éves realisztikus célpiac
90–400 iroda
A konzervatív SAM-mag ~10–15%-a. Bevételi mérföldközök:
€200K (2027) → €500K (2028) → ~€800–1.2M (2029)
(avg. €5 000/iroda/év).
Fájdalom-intenzitás szerinti rétegzés: a SAM szerkezete
A rétegzés alapja az
egyidejű közös aktív projektek száma
: ugyanaz a mérhető változó, amelyen a licencmodell kapacitás-tengelye is vált (2/5/15 aktív projekt). Így a piaci réteg és a tier-besorolás egyetlen közös metrikán függ, a piacméret és a bevételi modell mechanikusan összekapcsolódik. A rétegzés a "rendszeresen Revit-es partnerrel dolgozó" állományra épül (globálisan 5 000–10 000 iroda, a 02. szekció szűrési láncából).
Réteg
Definíció
Arány (belső becslés)
Becsült irodaszám
Természetes tier
A: folyamatos
2+ egyidejű közös projekt, állandó heti szinkron-igény
~15–25%
750–2 500
Studio
B: szakaszos
1 közös projekt, mérföldkő-alapú csere
~35–45%
1 750–4 500
Professional
C: eseti
3–6 havonta egy IFC-átadás, batch-konverzióval kezelhető
~30–50%
1 500–5 000
Community (ingyenes)
A számítás lépései:
fizetőképes fájdalmú piac
= A réteg + B réteg fele = ~1 600–4 700 iroda;
konzervatív SAM-mag (tervezési alap)
= ennek ~55–60%-a = 900–2 800 iroda. A diszkont a validálatlan konverziós realizmust (bizonyítatlan fizetési hajlandóság, elérési korlátok) képviseli: explicit, felülvizsgálható tényezőként, nem a szűrési láncba rejtve. A korábbi, attitűd-alapú levezetés ("parametrikus érettség + vásárlási hajlandóság", 02. szekció) ugyanebbe a 900–2 800-as sávba fut: a két független út konvergenciája erősíti a becslést, de mindkettő belső becslés marad.
Validálási feladat a design partner-körnek
A rétegarányokra (15–25% / 35–45% / 30–50%) nincs iparági adat: belső becslések. Az első design partner-kör természetes feladata a kalibrálás: hány egyidejű közös projektet visznek, milyen gyakori a csere, és mekkora a tényleges fizetési hajlandóság rétegenként. Ezek az adatok a rétegarányokat és az ~55–60%-os realizmus-diszkontot is mérhetővé teszik.
A TAM határai: a tartalom-készítés mint jövőbeli bővülés
A fenti TAM/SAM/SOM az Archicad–Revit adatcsere piacon alapul, és kizárólag az indulási termékkörre vonatkozik. A VSE-alapú, többformátumú tartalom-készítés és a gyártói szegmens nem része az indulásnak, így ezek a számok nem kalkulálnak velük. A gyártói bővülés mértéke azonban már nem teljesen méretlen: a NODU Creator (Content Engine) blueprint saját bottom-up becslése niche-TAM ~0,3–2 Mrd USD, EU SAM ~1 500–3 500 számla, 3 éves SOM 20–50 fizető ügyfél (lásd a dokumentum eleji, gyártói szegmensről szóló callout-ot). Ezek a számok a Creator-kezdeményezés saját tervezési alapjai: a Bridge-számokhoz nem adódnak hozzá.
Három szám, három szerep: melyik mire való
A dokumentum három, eltérő definíciójú SAM-jellegű számot használ, és ezek nem keverendők. (1)
Konzervatív mag: 900–2 800 iroda
, a fenti intenzitás-rétegzés eredménye realizmus-diszkonttal;
ez a bevétel-tervezés és a SOM-számítás alapja
(a 02. szekció korábbi, attitűd-alapú szűrési lánca ugyanebbe a sávba fut). (2)
Fizetőképes fájdalmú piac: ~1 600–4 700 iroda
, az A réteg + a B réteg fele, diszkont nélkül; ez a strukturális felső határ, amit a validáció mozgathat. (3)
Tágabb mixed-tool átfedés: ~1 400–3 600 iroda
, a lenti regionális tábla SAM-oszlopának összege, az „aktív mixed-tool átfedés" definícióval (a bottom-up piackutatási módszertan Európára 1 900–3 500, az USA-ra 250–560, Ázsiára 170–450 céget becsül; teljes forrásjegyzék a
Piackutatás
dokumentumban),
független módszertani keresztellenőrzés
, amely a (2)-vel azonos nagyságrendbe fut. A módszertanok irányukban megegyeznek: Európa a lényegesen nagyobb és elsődleges piac, az USA kisebb, prémium szegmens. A go-to-market prioritásnál és a bevételkalkulátor régió-választójánál a piackutatás névvel azonosított forrásokra (6sense, USP Research, ACE 2024, AIA 2024) épülő számai az irányadók.
Regionális bontás a piac geográfiai koncentrációja
A lenti tábla SAM-oszlopa a tágabb, „aktív mixed-tool átfedés" definíciót követi (összege ~1 400–3 600 iroda): a regionális arányok és a prioritás-sorrend a lényeg, nem az abszolút számok; a bevétel-tervezéshez a konzervatív mag (900–2 800) az irányadó.
Régió
TAM (iroda)
SAM (iroda)
SOM 3 év (iroda)
Prioritás
DACH + Kelet-Közép-Eu
5 000–8 000
750–1 600
37–160
Elsődleges
Nyugat-Európa (FR, BE, NL)
2 000–4 000
300–800
15–80
Másodlagos
Észak-Európa (Skandinávia)
1 000–2 000
150–400
7–40
Harmadlagos
USA
900–1 500
90–255
5–26
Premium szegmens
Ausztrália + egyéb
1 000–2 500
150–500
7–50
Hosszú táv
Az USA kisebb abszolút számot jelent, de az átlagos szerződési érték magasabb lehet. Az USA-ban az Archicad-es irodák rendkívül erős Revit-nyomás alatt dolgoznak, hiszen a partnerpiac 63,5%-a Revit-es. A SaaS-megoldások iránti befogadókészség és a fizetési képesség szignifikánsan magasabb, mint Kelet-Közép-Európában. Az USA-ban egy Studio tier deal átlagértéke reálisan €8 000–15 000/év lehet, az erősebb enterprise pricing kultúra miatt.
A valódi döntéshozói szám
A fenti irodaszámok mögött a modellek összefésülését ténylegesen végző szakemberek állnak: nagyobb irodákban dedikált BIM koordinátor, kisebbeknél hibrid szerepben egy építész. Irodánként jellemzően egy (nagyobbaknál két) ilyen személlyel és a konzervatív SAM-maggal (900–2 800 iroda) számolva az elérendő szakmai populáció nagyságrendileg 1 000–4 000 fő, a fizetőképes fájdalmú piac felső szélén sem több ~5 000-nél. Független felmérés erre nincs: belső becslés. Ez az a populáció, amelyet el kell érni BIM koordinátori közösségeken, Graphisoft fórumokon és AEC LinkedIn csoportokon keresztül.
06 Az USA piac különleges helyzete
Miért jelent az USA más kockázat-hozam profilt?
Az USA-ban a Revit-hegemónia annyira erős, hogy az Archicad-es iroda számára a Revit-kompatibilitás nem opcionális, hanem pályázati és szerződési követelmény. Az AIA és a General Services Administration (GSA, szövetségi ingatlankezelés) BIM-követelményei Revit-kompatibilis kimeneti formátumot várnak el számos közprojekten. Az USA-ban tehát az Archicad-es iroda a NODU Bridge-et nem „kényelemként" vásárolná, hanem projekt-hozzáférési feltételként.
Az USA mint premium szegmens miért?
Dimenzió
Európa (DACH, KKE)
USA
Archicad-es iroda Revit-es partnereinek aránya
~55–65%
~75–85%
BIM-mandátumok hatása
Közepes (egyes EU tagállamokban)
Erős (GSA, állami szint egyre több helyen)
SaaS-megoldások iránti befogadókészség
Közepes
Magas
Átlagos szerződési érték (várható)
€3 000–€8 000/év
€6 000–€15 000/év
Értékesítési ciklus
3–9 hónap
3–12 hónap (enterprise döntések lassabbak)
Értékesítési csatorna
Közvetlen + Graphisoft partner
Közvetlen + AEC konferenciák (AIA, AU)
Az USA piac kockázata
Az USA-ban az Archicad meglévő felhasználói bázisa kisebb és jobban szórt. A piacra lépési költség (értékesítés, support, jogi, helyi jelenlét) Európánál jóval magasabb. Az USA nem elsődleges terjeszkedési célpiac korai fázisban, de a beárazásnál és a referenciaszámoknál kiindulópont, és az első 5–10 USA-beli ügyfél szignifikánsan emelheti az átlagos szerződési értéket.
07 Nyitott kérdések
Amit nem tudunk és ami a piac valódi méretét eldönti
01
A kollaborációs sűrűség kérdése.
Az elemzés nem tudja mérni, hogy az Archicad-es irodák milyen arányban dolgoznak heti rendszeres Revit-adatcserével a negyedévente egyszeri IFC-átadással szemben. Ez a legkritikusabb ismeretlen: ha a „heti rendszeres" szegmens az irodáknak csak 10%-a, nem 55–65%-a, a SAM egy nagyságrenddel kisebb.
02
Graphisoft saját fejlesztési iránya.
A Graphisoft 2025-ös roadmap-ja mikrokernel-architektúrát és megerősített OpenBIM-kompatibilitást ígér. Ha a natív Archicad–Revit interop minősége 2–3 éven belül érdemi javulást mutat, a NODU Bridge értékajánlatának egy részét a platform szintjén lehet majd megoldani. Ennek valószínűsége és üteme nem ismert.
03
Az IFC-teher valódi megoszlása.
A dokumentált IFC-problémákat nagyvállalati, komplex projekteken mérték. Kisebb projekteken, amelyek az Archicad-irodák többségét teszik ki, ezek a számok alacsonyabbak lehetnek. Ez szűkíti az ROI-argumentum erejét a KKV-szegmensben.
04
Fizetési hajlandóság a KKV-szegmensben.
Az európai kis építész irodák (5–15 fő) hagyományosan alacsony SaaS-fizetési hajlandóságot mutatnak. Empirikusan nem tesztelt, hogy a €499/hó Studio tier mennyire megfizethető egy 8 fős irodának, ahol a BIM-koordinátor feladata csak részidős.
05
Az USA-beli Archicad-irodák elérhetősége.
Az USA-ban az Archicad-es irodák szétszórtan, de közösségileg aktívak: Mac-felhasználói kultúra, design-fókuszú praxis. Nem vizsgált, hogy ezek az irodák hogyan szereznek értesülést új eszközökről: AIA-konferencia, LinkedIn, Graphisoft reseller hálózat.
06
A Speckle V3 Archicad connector jövője.
Ha a Speckle következő fejlesztési ciklusa az Archicad parametrikus adatmegőrzésére fókuszál (ami eddig nem volt prioritás), egy ingyenes, community-supported alternatíva csökkenti a NODU Bridge differenciációját. A Speckle-sharp legacy repo 2026 május archív státusza erre utalhat, de a V3 connector fejlesztési priorizációja nem ismert.
07
A jövőbeli, többformátumú tartalom-készítési képesség megváltoztatja-e a piac méretét és határait?
Az elemzés az indulási termékkör Archicad–Revit adatcsere piacán alapul. A VSE-alapú parametrikus tartalom-készítés (és a vele párhuzamos, a gyártói szegmensre célzó NODU Creator kezdeményezés) nem része az indulásnak. Ha egyszer elérhetővé válik, és önálló értékajánlatot teremt a gyártói, GDL-specialista és Revit-orientált piacok felé, a releváns TAM lényegesen nagyobb lehet, mint a fenti számok mutatnak. Ennek mértéke empirikusan nem mért, és a jelenlegi adatokból nem számítható.
```

--------------------------------------------------

## FILE: nodu-bridge-piackutatas.html
Source: c:\NODU\NODU Bridge Repo\nodu-bridge-piackutatas.html
```
N
NODU Bridge
Piackutatás
Piackutatás
A lead-generációs kalkulátor konverziós és piacméret-feltételezéseinek független forrásokkal alátámasztott háttere.
2026-07-01 · Belső tervezési dokumentum · poczai@nodu.build
A NODU Bridge egy eddig megoldhatatlannak tűnő problémát old meg: a fal, tető, padló és más építőelemek parametrikus átvitelét Archicad és Revit között. Ez a dokumentum három párhuzamos kutatás eredményeit foglalja össze, amelyek a bevételkalkulátor konverziós rátáit és régiós piacméret-feltételezéseit alapozzák meg.
Egy sales-asszisztált, akut fájdalmat oldó (painkiller) terméknél a független benchmarkok forrásonként erősen szórnak (15–70%), a védhető, konzervatív sáv 30–45%. A kalkulátor ennek alsó végét (30%) használja, mert a painkiller-prémium hipotézis az első fizető kohorszok validációjáig hipotézis marad. A tényleges Archicad↔Revit átfedés piaca
Európában
koncentrálódik, nem az Egyesült Államokban.
Az alábbi szintézis 2024–2026-os forrásokkal dolgozik. A számszerű állításokat forrással jelöljük, és következetesen elkülönítjük a független benchmarkot a gyártói marketingtől. Ahol nincs megbízható publikus adat, azt kimondjuk. Ez a dokumentum kifejezetten a bevételkalkulátor konverziós és régiós feltételezéseinek bizonyítéknaplója; a teljes piacméret-narratívához (TAM/SAM/SOM, Autodesk-költségstruktúra, USA-pozicionálás) lásd a
Piaci elemzés
dokumentumot.
01: A probléma
Az interoperabilitási fájdalom valós és számszerűsíthető
Az Archicad és a Revit közötti adatcsere ma jellemzően IFC-n keresztül történik. Az IFC statikus geometriát visz át, de elveszíti a parametrikus szerkeszthetőséget, ezért minden tervezési változásnál a fogadó csapatnak újra kell modelleznie vagy jelentősen át kell dolgoznia az elemeket. Ennek a problémának a költsége jól dokumentált iparági szinten.
Mutató
Érték
Megbízhatóság
USA interoperabilitási veszteség (2004)
15,8 Mrd USD / év
magas (NIST, módszertan közölt)
Újramunka aránya a projektköltségben
5–10%
közepes-magas
Konverzió utáni kézi tisztítás aránya egy migrációban
~90%
közepes
IFC export + import idő (worst-case)
3–4 h + 4–6 h
közepes (fórum-jelentések)
Az IFC oda-vissza konverzió mindkét irányban veszteséges
A falak, födémek és tetők gyakran generikus objektumként vagy In-Place családként érkeznek meg, és eközben elveszítik a parametrikus intelligenciát. A Revit→Archicad utat a hivatalos Graphisoft fórum egyik threadje egyenesen
„fundamentally flawed"
(alapjaiban hibás) megnevezéssel illeti. Akadémiai elemzések (MDPI, ResearchGate) öt éven át tartó vizsgálatban is megerősítik, hogy az IFC-verziók fejlődése ellenére az adat- és geometriaveszteség tartós marad.
A kereslet valós, de kielégítetlen
Nincs gyártói roadmap natív parametrikus Archicad↔Revit átvitelre. A létező részmegoldások (IFC, RFA/RVT geometria-export, Speckle, Rhino.Inside) vagy csak geometriát visznek át, vagy más eszközfilozófiát követnek. A gyakorló mérnökök több éven át, több fórumon (Graphisoft Community, Autodesk Community, OSArch) ismétlik ugyanazt a panaszt.
Őszinte korlát
Nem található publikus, kifejezetten az Archicad↔Revit esetre vonatkozó per-elem vagy per-revízió mérnökóra-szám. Az iparági újramunka-adatok általánosak (minden BIM-interoperabilitás). A saját óra-becslésünk ezért modellezett, nem hivatkozható tény.
Források
NIST GCR 04-867: Cost Analysis of Inadequate Interoperability
Graphisoft Community: „Revit IFC to Archicad is fundamentally flawed"
BIM Heroes: Archicad to Revit migrációs útmutató (90% utómunka)
MDPI: BIM Interoperability via the IFC Standard (akadémiai)
02: A piac
A piac súlypontja: Európa, nem Amerika
A NODU Bridge célpiaca azoknak a cégeknek a metszete, amelyek mind Archicadet, mind Revitet használnak, vagy a kettő között kénytelenek modellt átadni. A bottom-up becslés régiónként:
Régió
Aktív mixed-tool cégek
USA
250–560
Európa
1 900–3 500
Ázsia
170–450
Globális aktív
3 000–5 000
Az ok strukturális. A Revit az USA piacának ~60–65%-át uralja, az Archicad ott csak ~3–8%-ot, így a kettő metszete szűk niche. Az Archicad ezzel szemben európai-natív, és az Open BIM mandátumok (Egyesült Királyság, Németország, skandináv országok) tovább növelik az eszközváltásra kényszerülő cégek számát. A teljes régiónkénti Revit/Archicad szoftverrészesedési tábla (Németország, UK, DACH, Kelet-Közép-Európa, Ausztrália) a
Piaci elemzés
01. szakaszában található.
Stratégiai következmény
A go-to-market elsődleges piaca Európa, nem az USA, ezért a kalkulátor alapértelmezett régiója is Európa. Az amerikai niche kicsi és prémium, a magasabb konverzió mellett 2–3 év alatt telítődik, míg Európa 5–7-szer nagyobb futásteret ad. Egy más módszertanú, független elemzés (lásd Piaci elemzés) is ugyanerre a következtetésre jut: DACH+CEE elsődleges, USA prémium szegmens. Két független becslés ugyanoda jut.
Fizetési hajlandóság (WTP) benchmark
Az összehasonlítható eszközkategória (interop, modell-QA, koordináció: BIMcollab, Speckle, Solibri) árazása alátámasztja a jelenlegi €199/Koordinátor/hó Professional pozíciót: ez a commodity BCF/issue-eszközök felett, a prémium modell-ellenőrzők sávjában helyezkedik el. Fontos, hogy a Bridge nem a szerzői szoftvereket (Revit, Archicad) váltja ki - azok ára csak költségvetési kontextus, nem viszonyítási alap. A teljes árazási tábla a
Piaci elemzés
03. szakaszában található.
Források
6sense: Autodesk Revit piaci részesedés
USP Research: Európai építészek BIM/CAD szoftverhasználata
Architects' Council of Europe: 2024 Sector Study
AIA: 2024 Firm Survey Report (USA cégszámok)
Markets&Markets: BIM szoftverpiac mérete régiónként
03: A konverzió
Konverziós benchmarkok sales-asszisztált painkiller termékekre
A független 2024–2026-os benchmarkok szerint a konverziós ráta erősen függ a motiontól (az értékesítési mechanizmustól):
Motion
Konverzió
Relevancia a NODU Bridge-re
Tiszta freemium (nyílt végű)
2–8% (medián ~4,5%)
az önkiszolgáló konverzió referenciapontja
Opt-in trial (kártya nélkül)
8–14%
–
Opt-out trial (kártya kötelező)
40–60%
–
Sales-asszisztált trial (GrowthSpree)
35–70% (medián 55%)
a demó-vezérelt tölcsérünk, de lásd lent: más forrás 28–42%-ot, illetve 15–30%-ot mér
Demo-only (enterprise)
55–75%
nagyobb Enterprise-ügyletek
Egy sales-asszisztált, painkiller-jellegű terméknél a védhető demó→ügyfél sáv
~30–45%
: a GrowthSpree 55%-os mediánja a legoptimistább forrásból származik, más benchmarkok (ADV.me 28–42%, egyéb 15–30%) lényegesen alacsonyabbak; a szórás a „sales-asszisztált" eltérő definícióiból fakad. A kalkulátor a 30%-ot használja alapértelmezettként (a sáv konzervatív vége), a felső tartomány (45%-ig) csúszkával elérhető.
Painkiller vs. vitamin: a szorzó realitása
A „painkiller" (akut fájdalmat oldó) termékek konverziója jellemzően magasabb, mint a „vitaminoké" (jó, de nem sürgető). A mobilalkalmazás-piacon ez a különbség akár 9-szeres is lehet (37% vs. 4%), de ez mobilapp-adat.
B2B-ben a reális szorzó 3–5×
, mert az értékesítési ciklus és a több döntéshozó kiegyenlíti a különbséget. A szűk vertikumú (niche ICP) szoftverek a generikus átlag 2–3-szorosát hozzák, és jobban megtartják az ügyfeleket (91% vs. 78–85% bruttó retenció).
Kaveát
A „painkiller" besorolás egyelőre hipotézis: attól, hogy mi annak látjuk, a felhasználó még nem feltétlenül így éli meg. Validáció: az első kohorszok aktiválási sebessége, a trial→fizető arány és az árérzékenység. Emellett nincs publikus konverziós adat kifejezetten a Revit/Archicad plugin-ökoszisztémára, így a számunk modellezett, forrásolt becslés.
Források
ADV.me 2025: SaaS free trial konverziós benchmarkok
GrowthSpree 2026: Trial-to-paid benchmarkok motion és ACV szerint
1Capture: Free-to-paid benchmarkok (10 000+ SaaS cég)
Airbridge: Painkiller vs Vitamin konverzió
SaaS Magazine: Vertical SaaS retenció és konverzió
04: A kalkulátor kalibrációja
A kalkulátor konverziós és piaci kalibrációja
Önkiszolgáló konverzió:
8% alapértelmezett a Professional/Studio ügyfelekre, sales-közreműködés nélkül; ez az 5–8%-os Free→Paid benchmark felső határa (a legjobb vertikális SaaS-benchmarkok plafonja is csak 5–6% körül van).
Sales-asszisztált demó→ügyfél arány:
30% alapértelmezett, kizárólag az Enterprise-jelölt leadekre (a sales-asszisztált painkiller sáv konzervatív vége); a 45%-ig terjedő felső tartomány csúszkával elérhető (a GrowthSpree-forrás magasabb, 55–70%-os számai a legoptimistább becslésből származnak, más források ennél lényegesen alacsonyabbak).
Régiós fókusz:
Európa az elsődleges piac (1 900–3 500 aktív mixed-tool cég), az USA (250–560) és Ázsia (170–450) kisebb, gyorsan telítődő niche.
Csatorna-megoszlás:
a leadek túlnyomó része (jellemzően ~90%) önállóan konvertál, csak az Enterprise-jelölt szelet (~8–10%) megy sales-asszisztált demó-tölcsérbe, amit egyetlen sales munkatárs kapacitása (~40 lead/hó) bőven fedez.
A reális kép
A havi forgalmat két, egymástól független csatorna adja: az önkiszolgáló Professional/Studio konverzió (a volumen nagy része, sales nélkül) és a sales-asszisztált Enterprise-tölcsér (kis volumen, magasabb egyedi érték). A növekedés fő hajtóereje az önkiszolgáló konverziós ráta és a lead-volumen, nem a sales-kapacitás. Ez egy modellezett projekció, amit az első fizető kohorszok valós adatai pontosítanak.
05: Korlátok
Őszinte adathiányok és a következő validációs lépések
A konzervatív hangnem megtartása érdekében kimondjuk, mit nem tudunk megbízhatóan:
Nincs publikus per-elem vagy per-revízió mérnökóra-szám az Archicad↔Revit esetre: a fájdalom iránya bizonyított, a pontos óraszám modellezett.
Nincs nyilvános konverziós adat a Revit/Archicad plugin-piacra: a 30% becslés analóg (sales-asszisztált vertical SaaS) benchmarkokon nyugszik.
A regionális CPL- és konferencia-paraméterek modellezett feltételezések; a kutatás nem adott hard regionális CPL-t.
A „painkiller" besorolás hipotézis a validációig.
Mit kell validálni az első 2–3 hónap után
Tényleges lead-szám csatornánként és régiónként; a lead→demó és demó→ügyfél arány a valós kohorszokon; az aktiválási sebesség (mennyi idő alatt jut el a felhasználó az első sikeres parametrikus átvitelig); valamint az árérzékenység. Ezek mentén a kalkulátor feltételezései pontosíthatók.
NODU Bridge Piackutatás v1.0  ·  2026-07-01  ·  Belső tervezési dokumentum  ·  A számszerű állítások független 2024–2026-os forrásokon alapulnak  ·  poczai@nodu.build
```

--------------------------------------------------

## FILE: nodu-bridge-roadmap.html
Source: c:\NODU\NODU Bridge Repo\nodu-bridge-roadmap.html
```
N
NODU Bridge
Belső / befektetői anyag
Termék-roadmap: Bridge → Build
A NODU Bridge önálló al-termékként indul, de a tágabb célja a teljes
nodu
platform (Building Information Graph, ERP, gyártás, beszerzés) felé vezető út megnyitása. Ez a négy fázis a `nodu.bridge` kapcsolati rétegtől a `nodu.build` teljes CAD-authoring platformig ível, a Phase 4 explicit célja az érték-inflexiós pont egy tervezett €25M-os befektetési körhöz. A licenc- és árazási modell dokumentumai jelenleg kizárólag a Bridge-re vonatkoznak, lásd a Licencmodell dokumentumot.
2026-07-03 · frissítve 2026-07-06
Kapott termékfejlesztési roadmap alapján
Státusz: nem megerősített munkaanyag
Belső dokumentum
Státusz (2026-07-06): a fázisterv nem megerősített
A forrásdokumentum két rétegből áll: egy fejlesztői állapotlistából és egy abból AI-eszközzel generált fázistervből, a kettő több ponton ellentmond egymásnak (részletes összevetés lentebb). A döntés szerint egyik réteg sem végleges: a dokumentum munkaanyag, a fázisterv dátumai és tartalma a fejlesztési vezetővel véglegesítendők. Egy 12 pontos tisztázó kérdéssor kiment (2026-07-06); a válaszok megérkezéséig a stratégiai és árazási dokumentumok nem igazodnak ehhez a roadmaphez, és az alábbi fázisleírás sem tekintendő vállalt ütemtervnek.
Nyitott kérdés: a sync tartalma és időzítése ütközik az árazási modellel
A "Delta-only syncing" kizárólag az AI-fázistervben szerepel (Phase 3, 2026 nov – 2027 jan); a fejlesztői állapotlista sehol nem említi. A fejlesztői lista ráadásul a konnektort elemtípusonként építi (lásd lentebb), vagyis a szept. 15-i GA szinkron-képessége legjobb esetben is részleges elemkörre terjed ki. A
Licencmodell
dokumentum ugyanakkor az élő, inkrementális szinkront a Professional tier launch-kori fő funkciójaként hirdeti. A fejlesztési vezető válaszáig a launch-kommunikációban az élő inkrementális szinkron nem ígérhető azonnal elérhető funkcióként.
Fejlesztési valóság
A fejlesztői állapotlista, és ahol ellentmond a fázistervnek
A forrásdokumentum eleji fejlesztői lista a Revit→Archicad konnektort elemtípusonként építi. A v1-es körben a falak készen vannak, a kivágásokon dolgozik a csapat, ezt követik a födémek és a nyílászárók. Az oszlopok, gerendák és függönyfalak a v2-be, az MEP a v3-ba sorolt. Utóbbi a dokumentumban is kérdőjellel.
v1 · kész
Falak
v1 · folyamatban
Kivágások
v1 · hátravan
Födémek
v1 · hátravan
Nyílászárók
v2
Oszlopok, gerendák, függönyfalak
v3 · kérdőjeles
MEP
Munkahipotézis (2026-07-06, a fejlesztési vezetővel megerősítendő): a v1 konnektor egyirányú, Revit→Archicad. Ez a licencmodell fizető-fél logikájával összefér (az Archicad-oldali, koordinációt vivő iroda a fogadó fél), de a kétirányú "Archicad↔Revit élő szinkron" launch-kommunikációt nem támasztja alá.
A fejlesztői lista és az AI-fázisterv közötti fő eltérések:
Terület
Fejlesztői lista
AI-fázisterv
Következmény
Fizetési rendszer
v2-es tétel
GA (szept. 15.) = "első bevétel"
GA-kor nincs számlázási képesség: a launch-kori ingyenes időszak nem döntés, hanem technikai kényszer; fizetés legkorábban a v2 megérkezésekor.
Felhő-hosting
Digital Ocean + devops-mérnök felvétele a v2-ben
Managed Kubernetes "az első naptól"
Nyitott kérdés, min fut a backend a GA-nál.
Delta-only szinkron
Nem szerepel
Phase 3 tétel
A tétel fejlesztői megerősítése hiányzik: a licencmodell fő funkció-ígéretének alapja bizonytalan.
State engine, task management
v3
Phase 2
A fázistartalmak a két réteg között elcsúsznak: a fázisterv funkció-hozzárendelése nem megbízható.
Verziókövetés, előzmények
v2
Phase 3
SSO / on-premise
Sehol nem szerepel (v1–v4)
Nem nevesíti
A 2027 eleji Enterprise-tier megnyitás fejlesztési feltétele (governance-képességek) nincs alátámasztva.
Termékfejlesztés
A négy fázis
Az alábbi négy fázis a forrásdokumentum AI-generált összefoglalójából származik. A dátumokról nem tisztázott, hogy vállalt határidők vagy generált célértékek, a fázistartalmak pedig a fenti pontokon eltérnek a fejlesztői listától: a fázisterv a fejlesztési vezető válaszaiig irányjelzésként, nem ütemtervként olvasandó.
GA · 2026-09-15
€25M inflexiós pont
Phase 1
Phase 2
Phase 3
Phase 4
bridge v1
bridge v2
bridge v3 + build
nodu.build CAD
ma
09-15
11-10
2027-01-31
2027-06-30
A sávok hossza a naptári időtartammal arányos. A dátumok a nem megerősített AI-fázistervből származnak. A delta-only szinkron a Phase 3 sávban érkezik: a GA-hoz viszonyított távolsága a fenti nyitott kérdés tárgya.
Phase 1: The Connectivity Layer
Most – 2026-09-15
nodu.bridge v1
A fókusz kizárólag az alapinfrastruktúra megteremtése és a fő értékajánlat (zökkenőmentes adatcsere) bizonyítása.
Funkciók
Headless model server
HUB regisztráció
User onboarding / jogosultságkezelés
Core Revit schema converter
Infrastruktúra
Managed Kubernetes DigitalOcean-on / Scaleway-en, skálázható felhő-hosting az első naptól. A fejlesztői lista ennek ellentmond (DO-hosting és devops-felvétel v2-es tétel), lásd a fenti összevetést
GTM
PR és marketing blitz demó videókkal és influencer-partnerségekkel. Zárt béta 3-4 elkötelezett céggel, 80%-os feature-completeness mellett.
Phase 2: The Interactive Platform
2026-09-16 – 2026-11-10
nodu.bridge v2
Átmenet egy headless eszközből egy interaktív munkaterületté.
Funkciók
Web-alapú model viewer
Issue tracking, task management
Engine
State Engine bevezetése: objektum-szintű állapotátmenetek, automatizált triggerek/eventek felhasználó-definiált n8n akciókon keresztül
PowerBI-konnektorok
GTM
Gyártói partnerek bevonása, az ügyfélkör horizontális bővítése diszciplínák mentén.
Phase 3: The Intelligence Expansion
2026-11-11 – 2027-01-31
nodu.bridge v3 + kezdeti nodu.build komponensek
Adatterhelés optimalizálása és az AI mint alap felhasználói felület bevezetése.
Funkciók
Delta-only szinkronizáció (csak a változott adat)
Teljes előzménykezelés
Dokumentumkezelés (képek, PDF-ek, rekordok)
AI-integráció
Asszisztens AI PowerBI / dashboard-építéshez
Természetes nyelvű lekérdezések
Mobilapp adminisztrációhoz és adat-visszakereséshez
Phase 4: The CAD Revolution
2027-02 – 2027-06-30
nodu.build CAD platform
A tömeges érték-inflexiós pont a tervezett €25M-os befektetéshez: a NODU hídból elsődleges authoring-környezetté válik.
Funkciók
Teljes Visual Scripting Environment (VSE) kiadás
Generatív AI
nodu.ParametricFamily
-eszközök automatikus generálása a model serverben minden olyan parametrikus modellhez, amely megkerüli a VSE-t, natívan szinkronizálva Archicaddel és Revittel is
Fejlett eszközök
Épületszerkezet / homlokzat-generátorok (burkolat, függönyfal, nyílászárók)
AI rendering
Natív költségbecslés
Ökoszisztéma
A platform megnyitása harmadik féltől származó fejlesztők és CAD-pluginek felé
Pontosítás (2026-07-06): a VSE-alapú tartalom-készítés többformátumú képességként tervezett: a
nodu.ParametricFamily
kimenete nem Revit-kötött, ugyanaz a parametrikus definíció további CAD- és gyártói formátumokra is előállítható. Ezzel párhuzamos, átfedő kezdeményezés a NODU Creator (Content Engine): knowledge-graph-alapú termékadat-motor a gyártói szegmensre, lehetséges önálló termékként, saját blueprint-tel (2026-06-11, v2.0) és saját ütemtervvel. A vezetőség az irányt támogatja; a két kezdeményezés közös generálási magjának határvonala és a részletes kidolgozás későbbre ütemezett.
Végrehajtási alap
Mérnöki realitás & infrastruktúra
Technikai adósság
Közel nulla. Az architektúra teljes egészében saját fejlesztésű, nem támaszkodik meglévő technológiai gyorstapaszokra, ezért a mérnöki kapacitás túlnyomó része feature-fejlesztésre és skálázásra fordítható, nem legacy-kód refaktorálására.
Infrastruktúra-stratégia
A Managed Kubernetes DigitalOcean-on / Scaleway-en biztosítja, hogy a platform elbírja a Revit schema converter és a jövőbeli generatív AI-funkciók compute-igényes terhelését, anélkül hogy korán belezárna a nagy hyperscalerek magasabb költségszintjébe.
Kiadási protokoll
Belső tesztelés 80%-os completeness-ig, mielőtt a zárt béta elindul a 3-4 célcéggel: ez biztosítja, hogy a szept. 15-i GA-launch stabil és azonnali fizetés-kiváltásra optimalizált legyen.
Forrás-megjegyzés (2026-07-06)
A fenti három állítás a forrásdokumentum AI-generált összefoglalójából származik, fejlesztői megerősítés nélkül. A "azonnali fizetés-kiváltás" a fejlesztői listával ütközik (fizetési rendszer csak a v2-ben), az infrastruktúra-állítás szintén (DO-hosting v2-es tétel), a "közel nulla technikai adósság" pedig nem validált önértékelés. Mindhárom a kiküldött tisztázó kérdéssor tárgya.
```

--------------------------------------------------

## FILE: nodu-bridge-speckle-tanulsagok.html
Source: c:\NODU\NODU Bridge Repo\nodu-bridge-speckle-tanulsagok.html
```
Stratégiai elemzés · pozicionálás
Pozicionálás és modell-tanulságok versenykörnyezet és árazási logika
Hol áll a NODU Bridge a piacon, mit tanulunk a meglévő AEC adatplatformok árazási modelljeiből, miért nehéz technikailag a probléma, amit megoldunk, és hogyan épül fel ebből a NODU Bridge saját licenclogikája.
Belső stratégiai dokumentum
2026-06-15 · frissítve 2026-07-06 (két külső szakértői felülvizsgálat után)
Forrás: nyilvános AEC platform-dokumentációk, Archicad–Revit mapping analízis
01 Pozicionálás
A NODU Bridge a versenykörnyezetben mit tanulunk a piactól, és hol térünk el
A NODU Bridge két, egymással ontológiailag inkompatibilis platform (az Archicad GDL-alapú logikája és a Revit Family–Category rendszere) közötti parametrikus fordításra specializálódott, élő, inkrementális szinkronnal (csak a változott elemek mennek át), emellett batch-/egyszeri konverzióval. A termék értéke az átvitel minőségéből fakad abból, hogy ami átmegy, az parametrikus marad, nem degradálódik nyers geometriai objektummá. Ez a pozicionálás megkülönbözteti a NODU Bridge-et a piac többi szereplőjétől, amelyek jellemzően adathubok vagy általános fejlesztői platformok, nem konverziós motorok.
A licencmodell kialakításához több meglévő AEC és fejlesztői platform árazási logikája szolgál referenciaként. Az Autodesk APS, a Viktor.ai és a Hypar mellett a legrészletesebben dokumentálható közülük a Speckle, mint az egyetlen open-core AEC adatplatform, amelynek konverziós és árazási logikája nyilvános forrásokból (repository, changelog, fórumok, a 2024–2025-ös árazási változások kommunikációja) legalább részben rekonstruálható. Ezért a Speckle ebben a dokumentumban visszatérő referenciapont, de csak egy input a több közül, nem a modell szervező elve. Fontos, hogy az analógia mindegyik szereplőnél kizárólag az árazási struktúra szintjén érvényes, a value proposition szintjén nem: egy adathub annyi értéket teremt, amennyit a csatlakoztatott rendszerek, a NODU Bridge értéke viszont magából a fordítás minőségéből fakad.
Egy iparági fejlemény korlátozott relevanciájú, de említésre méltó jelzés: 2025-ben a piac egyik vezető adatplatformja az adatcsomag-alapú számlázásról szinkronizáción alapuló számlázásra váltott. Ez annyit jelez, hogy az adatmozgás az AEC adatplatformokon elfogadott számlázási metrika, a NODU Bridge modelljét azonban közvetlenül nem validálja: a mi értékmérőnk nem az adatmozgás mennyisége, hanem a parametrikus megőrzés minősége, és az árazásunk átalánydíjas, nem volumenalapú.
Fontos korlát: ez az elemzés egyik versenytárs belső adataira sem támaszkodhat, konverziós rátákat, churn-számokat vagy enterprise deal méreteket egyikük sem publikált. Az ebben a dokumentumban szereplő numerikus referenciaértékek iparági általános SaaS-összehasonlítókból és hasonló fejlettségű B2B platformok nyilvános adataiból vannak levezetve. Ezt a bizonytalansági szintet a dokumentum következetesen jelzi.
A NODU Bridge platform egy későbbi, jövőbeli iránya, a Revit Family objektumtervezés, egyszer olyan tartalom-alkotó területet nyithat meg, amellyel a jelenlegi piaci szereplők egyike sem foglalkozik; ez azonban nem része az indulási termékkörnek, és az árazási analógiát nem befolyásolja.
02 Árazási modell tanulságai
Négy strukturális tanulság a piac árazási modelljeiből
Átalánydíj-logika a tranzakciós árazás elkerülése
A piac érettebb szereplői tudatosan kerülik az API-hívásokra vagy adatvolumenre épülő, tranzakciónkénti számlázást. Az indok elsősorban megrendelői-pszichológiai: az AEC iparágban a projektdöntések irodavezetők és tervezési igazgatók kezében vannak, nem IT-osztályoknál. Egy nagy projektben a modellszinkronizálások száma hónapról hónapra tízszeresen változhat a részletes tervezési sprint és a finomítási fázis között. Ez kiszámíthatatlan számlákat termel, ami szerződéskötési szinten erős ellenállást vált ki. Az éves átalánydíjas modell stabil bevételt termel a platformnak, és tervezhető kiadást a vevőnek. A NODU Bridge ugyanezt a logikát követi: a Professional és a Studio csomagok éves átalánydíjas struktúrán alapulnak, a konverziók vagy szinkron-események száma nem befolyásolja a számlát. A kapacitás-korlát nem tranzakciós, hanem strukturális: az egyidejűleg aktív (élő szinkronban lévő) projektek számát limitálja a tier, ez kiszámítható, a vevő által előre látható határ, nem hónapról hónapra ingadozó számla.
Lock-in az automatizáción keresztül
A piacon megfigyelhető legfontosabb megtartási mechanizmus nem a funkciókészlet, hanem a workflow-beágyazódás. Minél több egyedi automatizációs kódot épít egy iroda egy platformon belül (szerver-oldali automatizálási scripteket, projekt-specifikus adatfeldolgozó logikákat), annál magasabb a tényleges váltási költség. Ez nem mesterségesen kreált lock-in: a scriptgyűjtemény valódi szellemi tőkét képvisel, amelyet az iroda munkatársai hoztak létre, és a saját folyamataikra optimalizáltak.
A NODU Bridge esetében az egyenértékű mechanizmus a mapping-script-könyvtár. Ahogy egy iroda felhalmozza a saját konverziós szabályait (GDL–Family megfeleltetéseket, koordináta-transzformációs profilokat, story-binding logikákat, egyedi paraméter-mappingeket), ezek a scriptek az iroda BIM-munkamódszerének részévé válnak. A NODU Bridge elhagyásának valódi ára nem a licencdíj elvesztése, hanem az újraépítési idő és az átmeneti minőségromlás. Jövőbeli irányként: ha a VSE-alapú parametrikus tartalom-készítési képesség egyszer elérhetővé válik, ez a mechanizmus tovább erősödhet: az iroda a konverziós logika (mapping scriptek) mellett tartalmi vagyont, többformátumú parametrikus sablonokat is felhalmozhatna (ugyanaz a definíció Revit Family-ként és más formátumokban is kiadható), kettős IP-eszközzé bővítve a lock-int. Ez azonban nem része az indulási termékkörnek.
A 2025-ös sync-alapú váltás: korlátozott relevanciájú iparági jelzés
Egy piaci vezető 2025-ös számlázási átstrukturálása a feature-alapú csomagoktól a szinkronizáción alapuló metrikák felé annyit jelez, hogy az adatmozgás az AEC adatplatformokon elfogadott számlázási alap. Ennél többet nem: egy versenytárs (részben monetizációs kényszerből fakadó) modellváltása nem piaci validáció, a NODU Bridge pedig épp nem volumenalapú, hanem átalánydíjas árazást követ.
Fontos fenntartás: a szinkronizáció volumene nem egyenlő a konverzió minőségével. Egy hub-modellben a sync-alapú metrika az adatátvitel mennyiségét méri, ami ott értelmes proxy. A NODU Bridge esetében a releváns értékmérő nem az átvitt bájtok száma, hanem az, hogy hány parametrikus elem maradt parametrikus az átmeneten keresztül. A BIG graph logikának tehát nemcsak az átvitel mennyiségét, hanem a parametrikus gazdagság megőrzésének arányát is rögzítenie kell: ez az a differenciáló adat, amellyel a NODU Bridge megkülönböztetheti magát az egyszerű geometriai konverziós eszközöktől.
A platform mint hosszú távú következő lépés: az induláskori megtartás két lábon áll
A referenciamodellekben a lock-in mechanizmus az automatizációs script-könyvtár. A NODU Bridge esetén az induláskori megtartás két elemre épül: a mapping-sablonkönyvtárra (az iroda felhalmozott konverziós logikája) és a kontrollált koordinációs ciklusokra épülő szinkron-workflow-ra, amely a projektek napi működésének részévé válik. Induláskor ennél több nincs: a Bridge önállóan áll meg, platform-tartalom nélkül.
Hosszú távon (a Build-fázisok platform-funkcióinak megérkezésével) ehhez adódik hozzá a harmadik réteg: a NODU platform-ökoszisztéma, amikor a lock-in már nem csupán "nehéz lenne lecserélni az eszközt", hanem "az egész ökoszisztémától kellene elválni". Ez a strukturálisan erősebb mechanizmus azonban jövőbeli állapot, nem induláskori tény: a launch utáni első év churn-feltevéseit a két induláskori lábra kell méretezni.
03 A probléma mélysége
Miért nehéz az Archicad–Revit konverzió és miért ez a mi árkunk
Az alábbiakban dokumentált hibák egy Archicad–Revit mapping analízisből származnak, a piac legrészletesebben elemezhető konverziós megoldása alapján. Nem egyetlen versenytárs kritikájaként szerepelnek itt: egyik meglévő platform deklarált célja sem volt a teljes parametrikus round-trip konverzió Archicad és Revit között. Ezek a korlátok azért relevánsak, mert meghatározzák azt a technikai problémateret, amelyben a NODU Bridge operál, és pontosan ez a probléma a mi versenyelőnyünk forrása. Az, hogy egy érett, jól finanszírozott platform sem oldotta meg ezeket a konverziós problémákat, egyszerre jelzi a probléma mélységét és a megoldás potenciális piaci értékét.
1. hiba Parametrikus intelligencia elvesztése
A dokumentált konverzió nem tudta megbízhatóan leképezni a GDL-objektumokat Revit Family-kategóriákra. Egy precízen definiált Archicad ajtó saját GDL scripttel, méreti paraméterekkel és anyagdefiníciókkal "Generic Model" elemként érkezett Revitbe. Fontos megkülönböztetés: a paraméter-
értékek
(adat) property-ként gyakran átmennek. Ami elvész, az a parametrikus
viselkedés
: a constraint-ek, a méretezhetőség, a típuslogika. Éppen ez a viselkedés-megőrzés a konverzió nehéz és értékes része. Ez nem szoftverhibaként értelmezhető, hanem a hard-coded sémaleképezés strukturális következménye: ha a konverziós motor nem ismeri az Archicad GDL-típusrendszer és a Revit Family-Category hierarchia közötti szándékolt megfeleltetést, csak a legkisebb közös nevező, a nyers geometria marad.
2. hiba Koordináta-rendszer torzulás
A két platform alapvetően eltérő módon kezeli a lokális koordináta-rendszereket, az alappontokat (Survey Point, Project Base Point) és az északi irányt. Tesztben Revitből Archicadbe küldött és változatlanul visszaküldött elemek rotációs torzulást szenvedtek. Ez szisztematikus, nem eseti probléma. A konverzió oda-vissza irányban kumulatív hibát halmoz fel. Helyszínközpontú tájolással dolgozó projekteknél (ahol a Survey Point és a Project Base Point eltér) az eltérés méter nagyságrendű lehet; georeferált modelleknél (EOV/UTM koordináták) akár kilométeres is, és a Revit belső geometriai kiterjedés-limitje miatt az import teljesen el is szállhat.
3. hiba Story vs. Level magasságkötési konfliktus
Az Archicad relációsan köti a falmagasságokat a Storyline-hoz (Home Story + eltolás). A Revit ezzel szemben független referenciasíkokat (Level) használ. Amikor a konverzió Revit falat importált Archicadbe, az algoritmus automatikusan megpróbálta alkalmazni az Archicad story-binding szabályait: a fal teteje a felette lévő szinthez csatlakozott, súlyos geometriai csonkítást okozva. Az alapvető probléma az, hogy a konverzió nem tett különbséget szerkezeti szintszabályozók és segéd-referenciasíkok között. A Revit modellekben a Levelek nem mindig szintek: lehetnek tetősíkok, álmennyezet-referenciák vagy szerkesztési segédvonalak. A megkülönböztetés formálisan létezik (a Level "Building Story" paramétere), de a gyakorlatban megbízhatatlanul karbantartott, ezért a konverzió nem támaszkodhat rá vakon: ezt a szemantikai bizonytalanságot a dokumentált konverzió egyáltalán nem kezelte.
4. hiba Tesszellációs élhibák szabadformájú geometrián
Az Archicad Morph elemek ilyen konverción keresztüli exportálásakor háromszögelés történt. Revitbe importáláskor a konverter nem tudott különbséget tenni puha és kemény élek között: az eredmény organikus felületek helyett drótváz-szerű poligonhálók lett. A vizuális eredmény építészetileg nem volt használható. Ez a korlát különösen az organikus homlokzatokkal vagy összetett tömegmodellekkel dolgozó irodákat érinti érzékenyen.
5. hiba Hierarchikus elemek (lépcsők, korlátok) a stabil toolset határain kívül
A lépcsők és korlátok rekurzív al-elem struktúrája kívül esett a dokumentált konverzió stabil export-import képességén. A konverziós logika nem kezelte a beágyazott al-elem hierarchiákat, a lépcsők egyszerűen nem konvertálódtak. A lépcsőelem mind Archicadben, mind Revitben komplex kompozit objektum: összekapcsolt lépéselemek, pihenők, tartószerkezeti referenciák és kapcsolódó korlát-definíciók alkotják. Ennek a hierarchiának flat sémává való visszavezetése a konverzió tervezési határain kívül volt.
Fontos kontextus
A vizsgált platformok egyike sem állította, hogy teljes körű parametrikus round-trip konverziót nyújt Archicad és Revit között. Ezek a korlátok a meglévő megoldások deklarált hatókörén kívül esnek. Az elemzés célja a probléma technikai mélységének megértése, nem versenytárs-kritika.
A második hibakör: amit a fenti lista nem fed le
A 2026-07-06-i szakértői felülvizsgálat hat további hibaosztályt azonosított, amelyek a napi gyakorlatban legalább olyan súlyúak, mint a dokumentált öt, és amelyekkel a NODU Bridge fejlesztésének és kommunikációjának számolnia kell:
Rétegrendes szerkezetek:
az Archicad composite skin-ek és a Revit compound layer-ek (core boundary, wrapping) megfeleltetése: a napi gyakorlatban gyakoribb fájdalom, mint a szabadformájú geometria.
Anyag- és attribútum-mapping:
Building Material + Surface vs. Revit Material: a kimutatások és a mennyiségszámítások erre épülnek.
IFC property setek és osztályozási rendszerek
(Uniclass/OmniClass/nemzeti): a BEP-megfelelés alapja; ha a szinkron elhullajtja, a modell szerződéses értelemben használhatatlan.
Fázisok/felújítás:
Archicad Renovation Filter vs. Revit Phases: az európai állomány jelentős része felújítási projekt.
Worksharing-ütközés:
ha a szinkron BIMcloud Teamwork és Revit workshared central modellbe ír, tisztázandó az elem-tulajdonlás és az ütközéskezelés.
GUID-stabilitás / elemkövetés:
az inkrementális szinkron alapfeltétele, hogy egy elem session-ök között mindkét platformon azonosítható maradjon.
Az utolsó kettő nem csupán hibaosztály, hanem az élő szinkron értékajánlatának
technikai előfeltétele
: a fejlesztési tervben kiemelt helyük van.
Amit a piac sosem célzott: parametrikus tartalom-készítés jövőbeli irány
A dokumentált hibák kivétel nélkül konverziós problémákat írnak le: meglévő Archicad-objektumok Revitbe való átmenete során keletkező adatveszteséget. Sem a meglévő platformok, sem a NODU Bridge indulási termékköre nem célozza új parametrikus tartalom tervezését. Ez egy teljesen különböző termékfunkció: a NODU platform egyik tervezett, későbbi fejlesztési iránya, amely (a 2026-07-06-i pontosítás szerint) többformátumú képességként (Revit Family és további CAD-/gyártói formátumok) nyithat tartalom-alkotó dimenziót az interop-eszközök kategóriáján túl. Párhuzamos, átfedő kezdeményezés a NODU Creator (Content Engine): knowledge-graph-alapú termékadat-motor a gyártói szegmensre, lehetséges önálló termékként (saját blueprint, 2026-06-11). Induláskor egyik sem része a terméknek.
04 Piaci összehasonlítás
Árazási összehasonlítás négy releváns szereplő
Platform
Modell
Value metric
Paywall
Tanulság a NODU Bridge számára
Speckle
Open-core, átalánydíj
Workspaces + szinkron-metrika
Governance (SSO/RBAC) enterprise szinten
Az átalánydíj és a 2025-ös sync-metrika validálja az adatmozgást mint értékmérőt; a governance-paywallt viszont a NODU szándékosan korábbra helyezi (lásd 05)
Autodesk APS
PaaS, fogyasztásalapú
Flex Tokens / API-hívások
Minden tranzakció fizetős
Negatív minta: kiszámíthatatlan számla nagy projekteknél, vásárlói ellenállás
Viktor.ai
Fejlesztő-fókuszú SaaS
Seats + publikált alkalmazások
Publikált appok száma és elérése
Részleges analógia: a "publikált script" modell közel áll a NODU Bridge marketplace logikájához (2027)
Hypar
Hibrid SaaS
Compute + privát munkaterek
IP-védelem, privát futtatás
Erős analógia a compute-lock-in logikára, de US-fókuszú, kis- és közepes irodák körében elterjedtsége korlátozott
Status quo: kézi IFC-workflow
Ingyenes (szabvány)
Munkaidő (rejtett költség)
–
Ez az elsődleges valós versenytárs: a BEP-ek gyakran szerződésben írják elő; rejtett ára €15–35k/iroda/év (2–3 aktív közös projekt mellett); ezzel szemben a Studio €5 988/év a teher 17–40%-a
Status quo: újramodellezés / referencia-link
Belső embernap-költség
Modellezői munkaidő
–
A legelterjedtebb valós gyakorlat, ha natív modell kell; a Bridge tényleges ár-benchmarkja az újramodellezés embernap-költsége, nem a platformok listaára
A legfontosabb negatív tanulság az Autodesk APS modell. Az AEC-ben a vásárlási döntések irodavezetők és tervezési igazgatók kezében vannak. Egy kiszámíthatatlan, tranzakciókhoz kötött számla büdzsészorongást teremt, amely a megbeszélés előtt véget vet az értékesítési folyamatnak. Az AEC-piac tolerálja a magasabb abszolút árakat, ha azok kiszámíthatók és éves kontraktus keretében tervezhetők. Ez a legfontosabb árképzési korlát az AEC szoftverpiacon, és ez indokolja, hogy a NODU Bridge átalánydíjas struktúrát alkalmaz a Professional és a Studio szinteken.
A beszerzési vitában azonban nem a fenti platformok ellen kell nyerni, hanem a status quo ellen. A szkeptikus BIM-vezető kérdései kiszámíthatók: "miért fizessek azért, amit a Graphisoft natív RVT-cseréje ingyen tud?" (válasz: a natív csere geometriát visz át, nem parametrikus viselkedést); "a koordinációs fájdalmunkat referencia-modell + BCF megoldja" (válasz: a Bridge akkor kell, amikor szerkeszthető natív modell kell a túloldalon); "mi történik az évenkénti Archicad/Revit verzióváltásnál?" (erre a 07. szekció nyitott kérdése ad keretet). Az értékesítési anyagoknak ezekre a kérdésekre kell felkészülniük, nem a platform-összehasonlításra.
05 Döntési logika
Négy döntési pont hogyan jutottunk a javasolt struktúrához
01
Az adatkonverzió commodity az ingyenes réteg szükséges, nem opcionális
Az alapvető geometriai konverzió egyre inkább elvárás, nem differenciátor. Bármely platform, amely az alapvető fájlcsere mögé paywallt helyez, elveszíti a piacot a nyílt forráskódú alternatívákkal szemben. Az ingyenes szintnek valódi értéket kell nyújtania: azt a meggyőző első élményt, amelynek hatására a felhasználó megérti, mit tud a NODU Bridge, amit más nem tud, de meg kell állnia az igazi differenciátor előtt.
Az ingyenes szint tehát nem jóindulat kérdése: az organikus növekedés és a virális terjedés előfeltétele egy olyan iparágban, ahol a termékek értékelése elsősorban peer-ajánlásokon alapul.
02
A parametrikus engine az 1. paywall nem a governance
Ez az a pont, ahol a NODU Bridge szándékosan eltér a hub-platformok modelljétől. Egy hub ingyenesen adja a konnektorokat, mert azok geometriát visznek át, ami commodity. A NODU Bridge konnektor ezzel szemben tartalmazza a parametrikus mapping engine-t, ami az alapvető IP. Ezt az ingyenes szintbe helyezni azt jelentené, hogy az értéket nem tartjuk meg.
A scriptmentés funkció a természetes paywall: a felhasználó megtapasztalja az értéket, látja, hogy az ajtó ajtóként érkezik Revitbe, mielőtt eléri a korlátot. Ez az az architektúra, amely a hub-modellekből nem vehető át változtatás nélkül, mert a NODU Bridge termék-logikája alapvetően különbözik: a konnektor maga a differenciátor, nem a rá épülő automatizáció.
Jövőbeli irány a VSE-alapú parametrikus tartalom-készítési képességhez: amikor egyszer elérhetővé válik, ugyanaz a Professional paywall mögé kerülhet, mint a mapping script engine. Ez tovább erősítené a paywall megindoklását. Induláskor azonban a Professional tier értékajánlata egységesen a konverziós intelligencia (script engine); a tartalom-készítés nem része az indulási termékkörnek.
03
A fizetős seat a funkciót követi, és a kétcéges valóságot is kezelnie kell
A fizetős Koordinátor-seat azé, aki a modellek összefésülését és a szinkron-sablonokat gondozza: nagyobb irodákban dedikált BIM-koordinátor, kisebbeknél hibrid szerepben egy építész. A vevő tehát mindenhol létezik, ahol a fájdalom létezik. (Belső kalibrációs megjegyzés: mivel a legtöbb irodában egyetlen ember végzi ezt a munkát, a Studio 2 seat-es értékajánlata önmagában a piac kisebbik részének releváns: a Studio-konverziós várakozásokat ehhez kell mérni.)
A Professional → Studio upgrade legerősebb, mérhető triggere a
2 egyidejűleg aktív projektes limit kinövése
: ez automatikus, a szoftver saját állapotából látható kapacitás-esemény. Másodlagos triggerek: a második koordinátor belépése, az API-integrációs igény, és az iroda-folytonosság (a koordinátor távozásakor a sablonkönyvtár átadhatósága), ez utóbbi valós félelem, de beszerzési döntést ritkán indít el önmagában.
Kétcéges alapelv (2026-07-06):
egy közös Archicad–Revit projektben a két platform tipikusan két különböző cégnél van. A licencelv:
az fizet, akinek a két szoftver közötti adatcsere az érdeke
, jellemzően a koordinációt vivő (Archicad-oldali) iroda. A partneroldali résztvevők a fizető fél méltányos használati keretéből, cégen átnyúlóan kapnak ingyenes User-seatet, a konnektor telepítése ingyenes. A kapcsolódó részletkérdések (adattulajdon, felelősségi határok, megbízói CDE-előírások szerinti megfelelés) a 07. szekcióban nyitott kérdésként szerepelnek.
04
Governance az Enterprise szinten: jövőbeli tier, terv szerint 2027 elejétől
Az Enterprise szinten a hub-platformok governance-logikája közvetlenül alkalmazható: SSO, RBAC, on-premise deployment, audit logging, SLA. Ezek nem funkciók, hanem szervezeti kontrollmechanizmusok. Az Enterprise vásárlási döntést nem funkcionális összehasonlítás vezérli, hanem jogi és compliance követelmények, IP-védelmi igények vagy nagyvállalati IT-biztonsági előírások. Az értékesítési mozgás alapvetően eltér a Professional/Studio szintektől: az Enterprise-egyezkedés IT-biztonságon, jogi osztályon és beszerzési osztályon keresztül zajlik, és az ár másodlagos szempont a megfelelőségi garanciákhoz képest.
Időzítés (2026-07-06-i döntés):
az Enterprise tier induláskor nem indul: a governance-képességek (SSO, on-premise) nem v1-képességek, a Platform Core pedig a Build-fázisokkal érkezik. A tier terv szerint 2027 elején nyílik meg; addig a nagy, egyedi igényű irodák egyedi ajánlatot kapnak. Ennek fontos következménye, hogy az az iroda, amelynek beszerzési feltétele az SSO vagy az on-premise futtatás, 2026-ban nem tud vásárolni: ezt a pipeline-ban explicit kezelni kell (mit tartalmaz az egyedi ajánlat, és mit nem ígérünk). A platform-hozzáférés a majdani Enterprise-értékajánlat része lesz, nem induláskori tény.
06 Paywall-architektúra
A NODU Bridge paywall-architektúrája hol áll az első fizetős vonal
A NODU Bridge és egy tipikus hub-platform strukturális különbsége nem a szintek számában rejlik, hanem az első paywall elhelyezkedésében.
Szint
Hub-platform (referencia)
NODU Bridge
Ingyenes
Konnektorok + alap geometria + közösségi hoszting
Alap geometria + preset scriptek (olvasás) + havonta 2 teljes modelles konverzió, elemszám-korlát nélkül
1. Paywall
(nincs intermediate tier)
Élő, inkrementális szinkron + saját sablon létrehozása/mentése (Professional, 149 EUR/Koordinátor/hó; a pontos határvonal a funkcionalitással együtt véglegesítendő)
2. Paywall
Második Koordinátor / User-plafon / aktív projekt-limit + közös sablonkönyvtár, API (Studio, 499 EUR/iroda/hó)
Enterprise Paywall
(jövőbeli tier, terv: 2027 eleje)
SSO, RBAC, on-premise, SLA
SSO, RBAC, on-premise + BIG graph + ERP-integráció, SLA + NODU platform-belépés, a tier megnyílásától; induláskor egyedi ajánlat
Value metric
Workspaces + Automate Credits
Elsődlegesen az egyidejűleg aktív projektek száma tierenként (a fájdalom-intenzitást követő kapacitás-tengely); emellett Koordinátor-seat, méltányos User-kerettel (a keret visszaélés elleni korlát, nem árazási elem)
Lock-in mechanizmus
Automate scriptek a dedikált szerveren
Induláskor: mapping-sablonkönyvtár + kontrollált koordinációs ciklusokra épülő szinkron-workflow. Hosszú távon: + NODU platform-ökoszisztéma
Az első paywall elhelyezkedése a modell legfontosabb architekturális döntése. Ha az első paywall túl korai (mielőtt a felhasználó megtapasztalja az igazi értéket), a konverzió alacsony, és az NPS negatív. Ha túl késői (miután a felhasználó már a teljes értéket megkapta ingyenesen), a fizetési hajlandóság csökken, mert nincs egyértelmű következő lépés.
A NODU Bridge esetében a munkahipotézis szerint a sablonmentés és az élő szinkron együtt adja a természetes határpontot: a felhasználó az ingyenes batch-konverzióval már tudja, mit kap, de a megszerzett tudást (a felépített mapping-logikát) csak előfizetéssel tarthatja meg, és a folyamatos szinkron-képességet is csak ott kapja meg. A szinkron pozicionálása (2026-07-06-i döntés):
kontrollált koordinációs ciklus
: a Koordinátor hagyja jóvá, mi és mikor megy át, nem felügyelet nélküli háttérfolyamat. Ez tudatosan illeszkedik az irodák minőségbiztosítási gyakorlatához (verzionált, ellenőrzött átadások, BCF-körök): a Bridge a mérföldkő-alapú cserét gyorsítja fel, és teszi veszteségmentessé, nem megkerüli azt. Két fontos fenntartás áll fenn. (1) A határvonal pontos meghúzása (mit tud a preset sablon, hol kezdődik a "saját" mapping) a végleges funkcionalitás ismerete nélkül nem zárható le: ez a licencmodell legfontosabb nyitott kérdése, a fejlesztéssel együtt véglegesítendő. (2) Nyitott roadmap-kockázat, hogy az inkrementális szinkron a GA-ra (2026-09-15) elkészül-e, vagy csak a Phase 3-ban (2026 nov – 2027 jan): ez a kérdés nem előzetes egyeztetéssel dől el, hanem magával a fejlesztési ütemtervvel: a valós státusz akkor válik ismertté, amikor a roadmap az adott fázishoz ér. Amíg ez nem történik meg, a launch-közeli sales- és befektetői kommunikációban óvatosan kell fogalmazni erről a funkcióról, és ha a szinkron csúszik, a Professional GA-értékajánlatát és árát ehhez kell igazítani (pl. bevezető árazás a szinkron megérkezéséig).
07 Nyitott kérdések
Amit nem tudunk nyitott kérdések és feltételezések
Az alábbi kérdések nem retorikai jellegűek. Ezek valódi bizonytalansági pontok, amelyek a licencmodell kalibrálását befolyásolják, és amelyekre jelenleg nincs adatunk.
01
A free → paid konverziós ráta (5–8%) AEC-specifikus adat hiányában becslés
A piaci referenciákat idéztük, de egyik platform sem tett közzé konverziós rátákat. Az 5–8%-os sáv a generikus 3–5%-os B2B SaaS-referenciaérték painkiller-pozícióval (akut, eddig megoldatlan probléma + szűk vertikum) felfelé korrigált változata, a 2026-07-03-i validáció szerint a legjobb vertikális SaaS-benchmarkok (pl. LegalTech) plafonja is csak 5,2–6,1%, a korábbi 6–10%-os sáv tehát a bizonyítékokhoz képest optimista volt. AEC-specifikus freemium konverziós adat nem létezik a nyilvános szakirodalomban. A tényleges ráta lehet alacsonyabb, mivel az AEC-irodák konzervatív technológia-adoptálók, ahol az eszközváltás döntési ciklusa hosszú. A 2026-07-06-i felülvizsgálat a sáv felső határát 5–6%-ra normálta: a 8% a saját idézett vertikális benchmark-plafon (6,1%) felett volt. Fontosabb vezérmetrika a konverziós rátánál az
aktiváció
: az első saját mapping-sablon megépítése és az első szinkron-kapcsolat beállítása: ez a két esemény jelzi előre a fizetővé válást és a megtartást, és rétegenként (A/B/C fájdalom-intenzitás) eltérő konverziót valószínűsít. Ez az a számkör, amely a licencmodell megtérülési kalkulációját leginkább befolyásolja, és jelenleg a legkevésbé megalapozott.
02
LEZÁRVA (2026-07-06): az elemszám-korlát gyakoriság-alapú korlátra cserélve
A 2026-07-06-i szakértői felülvizsgálat megállapította, hogy a korábbi 500 elemes kalibrációs keret (200–800 elemes "átlagprojekt" feltevéssel) nagyságrenddel melléfog: egy tipikus közepes Archicad épületmodell 30 000–150 000+ elem, egyetlen lakószint is bőven 500 fölött van. Az 500 elemes korlát tehát nem "pilot projekt", hanem részmodell-demó volt, amely a Community tier deklarált célját (valódi érték az eseti cserét futtató C rétegnek) nem teljesítette. Döntés: az elemszám-korlát megszűnt, helyette gyakoriság-alapú fair use-határ: havonta 2 teljes modelles konverzió. Ez pontosan a C réteg (3–6 havonta egy IFC-átadás) igényét fedi le teljes értékkel, miközben a gyakoribb használat (a szoftver saját állapotából mérve) a B/A rétegbe, tehát a fizetős tierekbe tereli a felhasználót. A végleges kalibrálás (havi 2 elég-e, vagy 1/3) az első 50 aktív felhasználó telemetriájából történik.
03
A sablon-lock-in feltételezi az aktív sablonépítést az élő szinkron ezt részben kompenzálja
A megtartási mechanizmus egyik fele feltételezi, hogy a Koordinátorok aktívan építenek és mentenek mapping-sablonokat. A valós workflow azonban nem folyamatos sablonépítés: a mapping-beállítás jellemzően projektindításkor egyszeri, intenzív munka (1–2 hét), utána hónapokig alig nyúlnak hozzá: a konverziós pillanat tehát a projektindítás, és az onboardingnak erre az egyszeri, nagy téttel bíró eseményre kell épülnie. A második megtartási szál a kontrollált koordinációs ciklusokra épülő szinkron-workflow, amely a projekt élete alatt a koordináció gerincévé válik (a teljes iroda ingyenes User-seatekkel), lemondása nem egy eszköz elhagyása, hanem egy működő koordinációs folyamat megszakítása.
Az onboarding célja ettől függetlenül változatlan: a Koordinátort el kell vezetni az első saját mapping-sablon megépítéséig és az első szinkron-kapcsolat beállításáig: ez a két aktivációs esemény a megtartás legjobb előrejelzője. Ha az onboarding egyiket sem éri el, a Professional tier nem termel megtartható értéket, és a megújítási arány alacsony marad.
04
Az átalánydíjas Studio csomag potenciálisan alulárazza a nagy szinkron-forgalmú irodákat
499 EUR/hó 2 Koordinátor-seat és a hozzájuk tartozó méltányos User-keret mellett fejenkénti bontásban alacsony összeg egy olyan iroda számára, amely napi szinten, éles projekteken futtat szinkront. Az átalánydíjas modell egyszerűsíti az értékesítést, de bevételt hagyhat az asztalon. A modellben a korrekciós mechanizmus már nem egy jövőbeli seat-alapú áttérés (az árazás eleve Koordinátor-seat-alapú), hanem a kapacitás-tengely kalibrálása: ha az adatok azt mutatják, hogy a Studio-irodák rendszeresen az 5 aktív projektes limit közelében járnak, vagy a 20 fős User-keretet kinövik, a limitek és az árak újrahangolása indokolt a tényleges felhasználási adatok alapján, nem előre rögzített ütemterv szerint.
05
Az Enterprise minimum (2 500 EUR/hó) piaci referencia nélkül meghatározott, és csak a tier 2027 eleji megnyílásakor lép életbe
Nincs közvetlen összehasonlítható adatunk egy Archicad–Revit parametrikus bridge enterprise deploymentjének árára vonatkozóan. A 2 500 EUR-os alsó határ a piac ismert enterprise árkategóriájából van levezetve, SMB-adjacent irodák felé lefelé korrigálva. A 2026-07-06-i döntés szerint az Enterprise tier induláskor nem indul: a floor a tier megnyílásakor (terv: 2027 eleje) lép életbe, addig egyedi ajánlatok élnek. A tényleges fizetési hajlandóság Enterprise szinten ismeretlen az első szerződések megkötéséig. Az Enterprise-árképzés mindig tárgyaláson alapul, és az első három-öt deal fogja meghatározni az indokolt árkategóriát és a sztenderd konstrukciót.
06
A Bridge → Platform Core upsell feltételezi, hogy az Enterprise ügyfél BIG graph-igényt fejleszt, hosszú távú kérdés, bevételi feltevés nélkül
A háromszintű stratégia (Bridge → Platform Core → Marketplace) feltételezi, hogy a majdani Enterprise Bridge-felhasználók természetes úton fejlesztenek igényt a BIG graph és az ERP-integráció iránt. Ez ésszerű hipotézis, de nem bizonyosság, és a 2026-07-06-i döntés szerint a jelenlegi piaci és bevételi számítások platform-upsell bevételt nem tartalmaznak, tehát ez a kérdés a tervezési számokat nem érinti. Az upsell-útvonalat a platform-fázisban explicit módon kell tervezni, aktív customer success munkával, amely a BIG graph használati eseteit az ügyfél konkrét fájdalompontjaihoz köti, nem pedig azt feltételezve, hogy az organikusan kialakul.
07
Az "egyidejűleg aktív projekt" definíciója nyitott: a fő value metric jelenleg kijátszható
Egy közös projekt nem folyamatosan aktív: tender/koncepció fázisban alig cserél, kiviteli fázisban intenzíven, megvalósulási szakaszban egyszer. Az irodák a projekteket deaktiválni-reaktiválni fogják, hogy a limit alatt maradjanak. Definiálandó, hogy mit őriz meg a deaktiválás (mapping-sablonok, elempárosítás), mekkora a reaktiválás súrlódása, van-e türelmi mechanizmus. A jelenlegi 60 napos inaktivitási szabály kiindulópont, de a projektciklus-viselkedésre nincs kalibrálva. Amíg ez nincs lezárva, a kapacitás-tengely (a licencmodell elsődleges value metricje) kijátszható.
08
Kétcéges működés részletkérdései: adattulajdon, felelősség, CDE-megfelelés
A licencelv lezárt (az fizet, akinek az adatcsere az érdeke; a partneroldal cégen átnyúló, ingyenes User-seateket kap), de a kapcsolódó kérdések nyitottak: kié a szinkronizált modell-tartalom a két cég közötti térben; ki felel egy hibás szinkron okozta kárért (szakmai felelősségbiztosítási kérdés); hogyan illeszkedik a szinkron a megbízói CDE-előírásokhoz (ISO 19650) és a worksharing elem-tulajdonláshoz. Ezek a kérdések minden komolyabb beszerzési átvilágításban elő fognak kerülni.
09
Verziókövetés és futtatási környezet: a kategória történelmi buktatói
Két kérdés, amelyet minden szkeptikus BIM-vezető fel fog tenni. (1) Verziókövetés: az Archicad és a Revit évente új verziót ad ki: mekkora az API-követési késés? A harmadik feles konverter-kategória korábbi szereplői jellemzően ezen véreztek el; a verziókövetési vállalás (pl. "az új verzió támogatása a megjelenéstől számított N héten belül") explicit ígéretté teendő. (2) Futtatási környezet: hol fut a szinkron: felhőben vagy lokálisan? Számos megbízói NDA tiltja a modell külső feltöltését, és az on-premise opció csak a 2027-es Enterprise-nyílással érkezik; addig tisztázandó, mit tudunk mondani az adatkezelésről (lokális feldolgozás, EU-s adattárolás, titkosítás).
Ezek a bizonytalanságok nem érvénytelenítik a javasolt modellt, de azt jelzik, hogy az első 6–12 hónap kritikus adatgyűjtési periódus. A free tier korlátja, a Professional ára és a Studio struktúrája mind felülvizsgálandó az első 50 aktív felhasználó viselkedési adatai alapján. A modell felülvizsgálati ciklusa nem naptár-alapú, hanem adatalapú kell legyen: az árazási döntéseket az adott mérföldkő elérésekor kell újragondolni, nem korábban és nem évek múlva.
```

--------------------------------------------------

## FILE: nodu-bridge-vezetoi-osszefoglalo.html
Source: c:\NODU\NODU Bridge Repo\nodu-bridge-vezetoi-osszefoglalo.html
```
N
NODU Bridge
Stratégiai áttekintés
NODU Bridge: a stratégiai kép egy oldalon
A NODU Bridge élő, inkrementális Archicad–Revit szinkront ad: csak a változott elemek mennek át, az elemek parametrikus logikája pedig megmarad. A batch/egyszeri konverzió emellett külön funkcióként elérhető. Ez az oldal a teljes dokumentumrendszer vezetői kivonata: a stratégiai alapelvek, a kulcsszámok, oldalanként a legfontosabb megállapítások és a döntést igénylő nyitott pontok.
2026-07-07
Belső vezetői anyag
6 dokumentum kivonata
Stratégiai alapok
Az alapelv, amelyre a modell ma épül
A fizetős seat a funkciót követi, nem a munkakört
A modellek összefésülése és a szinkron-sablonok karbantartása minden Archicad–Revit együttműködésben elvégzendő szakértői munka: nagyobb irodákban dedikált BIM-koordinátor végzi, kisebbeknél hibrid szerepben egy építész. A fizetős Koordinátor seat azé, aki ezt a munkát végzi, tehát a vevő mindenhol létezik, ahol a fájdalom is létezik. Az élő szinkron ugyanakkor a teljes irodáé: minden munkatárs ingyenes User seatet kap, a Koordinátor-seathez kötött, méltányos használati keretben: elindíthat egy meglévő sablont, de nem szerkesztheti azt. Az árazás a munkát követi, a hozzáférés az egész irodáé.
Jövőbeli irányok (nem indulási scope)
A Bridge mint platform-belépési kapu
A Bridge hosszú távon a NODU platform belépési kapuja: az irodák a Bridge-en keresztül ismerik meg a NODU-t, és ahogy a Build-fázisok platform-funkciói elérhetővé válnak, a meglévő ügyfélbázis kész upsell-úttá válik. Induláskor azonban a Bridge önállóan is megáll: az értéke maga a szinkron, platform-tartalom ekkor még nincs. A kapu-szerep a platform-tartalommal együtt, fokozatosan nyílik meg. A jelenlegi piaci, árazási és bevételi számítások platform-bevételt nem tartalmaznak, minden későbbi platform-bevétel efölötti tartalék.
VSE-alapú parametrikus tartalom-készítés + NODU Creator
A VSE-alapú parametrikus tartalomkészítés a platform egyik tervezett, későbbi fejlesztési iránya, a 2026-07-06-i pontosítás szerint többformátumú képességként: nem csak Revit Family, hanem további CAD- és gyártói formátumok előállítására is. Ezzel párhuzamos, átfedő kezdeményezés a
NODU Creator (Content Engine)
: knowledge-graph-alapú termékadat-motor, amely önálló termékként a gyártói szegmenst célozná meg B2B-úton (saját blueprint: 2026-06-11, v2.0), miközben a generálási mag a Bridge-platformon is jelen lenne. A vezetőség támogatja az irányt, a részletes kidolgozás későbbre ütemezett. Egyik sem része az induláskor szállított termékkörnek, és a jelenlegi piaci, árazási és bevételi számítások egyikkel sem kalkulálnak.
Kulcsszámok
A lényeg hat számban
€7 800–17 280
IFC-teher projektenként évente
Ezt a rejtett munkaidő-költséget váltja ki a Bridge
900–2 800 iroda
Kiszolgálható piac (SAM, konzervatív mag)
Fájdalom-intenzitás szerint rétegezve (A/B/C); a fizetőképes fájdalmú piac ~1 600–4 700
€199 / Koordinátor / hó
Professional belépőár
Studio €499/iroda/hó · Enterprise induláskor egyedi ajánlat (a tier a platform-fázissal nyílik)
2026-09-15
nodu.bridge v1 GA
Zárt béta 3-4 céggel a launch előtt
€200K (2027) → €500K (2028)
Éves ARR mérföldkövek · SOM: 90–400 iroda
Konzervatív számítás, első kohorszokkal kalibrálandó
€25M
Tervezett befektetési kör
Phase 4: nodu.build CAD platform, 2027 H1
Dokumentumok
Mi található az egyes oldalakon
Piaci elemzés
A célfelhasználó, a piac szerkezete, az IFC-fájdalom ára és a piacméret három horizonton.
€7 800–17 280
rejtett IFC-teher / projekt / év
A valódi célfelhasználó a BIM koordinátor, irodánként 1-2 fő, nem 15 seat
Európa-first: a DACH + Kelet-Közép-Európa az elsődleges piac, az USA kisebb, prémium szegmens
Az IFC-teher konzervatív becsléssel is a Studio-licenc többszöröse. Az ROI-érvelés munkaóra-alapú, nem szoftverhelyettesítés
Megnyitás
Piackutatás
A kalkulátor konverziós és piaci feltételezéseinek forrásolt bizonyíték-naplója.
1 900–3 500
aktív vegyes-platformos (Archicad+Revit) cég Európában
A fájdalompont függetlenül igazolt (NIST: 15,8 Mrd USD/év interop-veszteség; újramunka a projektköltség 5–10%-a)
A sales-asszisztált konverzió védhető tervezési sávja 30–45%: a korábbi, optimistább szám korrigálva
Önkiszolgáló free→paid: 5–8%, a 8% a felső eset, nem tervezési alap
Megnyitás
Licencmodell és kalkulátor
A négytieres licencmodell, a paywall-logika és az interaktív bevétel-eszközök.
€199
/ Koordinátor / hó (Professional)
Két lokálisan kikényszeríthető tengely: szerepkör (fizetős Koordinátor + ingyenes User, 1:10) és kapacitás (2 / 5 / 15 egyidejűleg aktív projekt)
Community ingyenes (batch-konverzió preset sablonokkal, havonta 2 teljes modell, elemszám-korlát nélkül): a fizetős vonal a script engine + saját sablonok
A launch elején ingyenes Studio-időszak tervezett, paraméterei még nyitottak. Az élő szinkron Phase 3-ban érkezik (2026 Q4), meglévő előfizetők automatikusan megkapják
Megnyitás
Pozicionálás és modell-tanulságok
Árazási minták a versenykörnyezetből és a technológiai buktatók, amelyekre a Bridge épül.
5
dokumentált konverziós hibaosztály, amit a piac ma nem old meg
Átalánydíj-logika: a tranzakció-alapú árazást az AEC-vásárlók elutasítják (Autodesk APS negatív minta)
Az első paywall tudatosan korai: a parametrikus engine az IP, nem a governance
Lock-in: a mapping-sablonkönyvtár + az élő szinkron a napi workflow-ban
Megnyitás
Enterprise esettanulmányok
Három nyilvános enterprise-eset iparági analógiaként: mi kényszeríti ki az Enterprise-váltást.
3+1
kategorikusan különböző enterprise-trigger
Jogi/szerződéses kényszer (ARUP), számítási kapacitás (Ramboll), IP-védelem (Herzog & de Meuron): más döntéshozó, más ciklus
Negyedik trigger: a platform-belépés, amely a legmagasabb LTV-t hozza
Következmény: trigger-specifikus üzenetküldés kell, nem egyetlen általános Enterprise-értékajánlat
Megnyitás
Termék-roadmap
Négy fázis a bridge v1 kapcsolati rétegtől a nodu.build CAD-platformig.
4 fázis
GA 2026-09-15 → nodu.build 2027-06-30
Phase 2: web viewer, State Engine, PowerBI (2026 ősz)
Phase 3: delta-only szinkron, AI-asszisztens, mobil (2026 nov – 2027 jan)
Phase 4: teljes VSE + generatív ParametricFamily, ez a €25M inflexiós pont
Megnyitás
Döntési napirend
Döntést igénylő nyitott pontok
Élő szinkron a launchkor – ELDÖNTVE
A delta-only szinkron a Phase 3-ban marad (2026 nov – 2027 jan). A launch-kori árazási kommunikáció nem hirdetheti fő funkcióként. Következő lépés: az árazási értékajánlat és a launch-üzenet újragondolása a szeptemberi kommunikáció véglegesítése előtt.
Community → Professional határvonal
Pontosan mi kerül a fizetős vonal mögé? Ez a preset sablon képességeitől függ, a fejlesztéssel együtt véglegesítendő.
Ingyenes Studio-időszak paraméterei
Az időtartam, a lejárat utáni fizetési kötelezettség és a pontos funkciókör még nyitott; a cégdoménhez kötött egyszeri beváltás már eldöntve.
Marketing-tevékenységek költsége nincs kalkulálva
A kalkulátor havi büdzsé-inputtal számol, de a roadmap GTM-tevékenységeihez (PR-kampány, demóvideók, influencer-partnerségek, konferencia-részvétel) nincs tevékenység-szintű költségterv. Ezt a launch előtt el kell készíteni.
Tier-limitek kalibrálatlanok
Az 1:10 User-arány, a 2/5/15 projekt-limit és a 60 napos inaktivitási ablak illusztratív kiindulópont, amelyet az első fizető ügyfelek adataival felül kell vizsgálni.
```

--------------------------------------------------

## FILE: README.md
Source: c:\NODU\NODU Bridge Repo\README.md
```
# NODU Bridge

NODU Bridge — a nyílt BIM/AEC szoftverintegrációs platform.

## Tartalom

Ez a repository a NODU Bridge projekt tartalmi oldalait és dokumentációját tartalmazza.

### HTML Oldalak

- **index.html** — Főoldal
- **nodu-bridge-dashboard.html** — Dashboard prezentáció
- **nodu-bridge-license-calculator.html** — Licenc kalkulátor
- **nodu-bridge-piackutatas.html** — Piackutatás
- **nodu-bridge-piac-elemzes.html** — Piacelemzés
- **nodu-bridge-roadmap.html** — Termék roadmap
- **nodu-bridge-vezetoi-osszefoglalo.html** — Vezetői összefoglalók
- **nodu-bridge-esettanulmanyok.html** — Esettanulmányok
- **nodu-bridge-speckle-tanulsagok.html** — Speckle tanulságok
- **nodu-bridge-lead-gen.html** — Lead generation oldal
- **bridge-waitlist.html** — Waitlist oldal

## GitHub Pages

A projekt GitHub Pages segítségével érhető el [nodubridge.zolkapoczai.com](https://zolkapoczai.github.io/nodubridge)-en.

## Licenc

Saját fejlesztés, 2026.
```

--------------------------------------------------
