# Peseteando PR · v2.1.1

**App:** https://fravier3.github.io/Peseteando/

PWA para iPhone y Android. Ofertas presenciales de Walgreens Puerto Rico, cupones que requieren activación, códigos online, favoritos y búsqueda. Conserva la URL y el almacenamiento local de la versión anterior. Sin cuenta propia, backend ni APIs de pago.

## Uso y verificación regional

El catálogo principal solo muestra `pr_status=official_pr`. El botón **Sin verificar** conserva las promociones de las fuentes generales que no tienen evidencia regional. La ausencia de una exclusión de PR no demuestra disponibilidad local.

- **Usar en tienda:** ofertas del shopper regional y cupones Walgreens IVC publicados con contexto explícito PR y canje POS.
- **Comprar online:** códigos de Walgreens.com o Photo. No se anuncian como códigos que se dictan a la cajera.
- **Recoger en tienda:** únicamente cuando los términos del código especifican pickup. Es una compra hecha online; el descuento se aplica antes de recoger.
- **Activar cupón:** enlace a Walgreens para guardar el cupón en la cuenta oficial; guardar un favorito en Peseteando no lo activa.
- **Kiosco de fotos:** canal adicional cuando los términos lo permiten; no es la caja de productos generales.

`official_pr` verifica publicación o condiciones regionales, no inventario ni un canje realizado. `redemption_tested` es falso en todas las ofertas actuales. Los precios, fotos, formatos y cantidades vienen de la fuente. No se inventa una fotografía de producto para un código general. Cuando no hay precio o presentación individual, se indica o se enlaza al grupo de artículos elegibles. Las recompensas futuras y cupones adicionales no se restan del precio anunciado.

## Filtro por sucursal

El campo **Tu Walgreens** acepta el número de sucursal (1–5 dígitos) del recibo o de su ficha oficial. Lo guarda solo en este dispositivo (`peseteando.store.v1`), independientemente de los favoritos. Oculta únicamente ofertas presenciales de Walgreens que incluyan ese número en `excluded_stores`; no deduce exclusiones para compras online, otros comercios ni ofertas sin restricciones publicadas. Un número sin exclusión expresa no verifica que exista la sucursal, su inventario ni el canje. El estado vacío explica cuándo las exclusiones causan que no aparezcan ofertas. Quitar el filtro restaura las ofertas, sin borrarlas ni eliminar favoritos.

## Fuentes y adaptadores

1. Códigos: https://www.walgreens.com/promotion/offer-details
2. Photo: https://photo.walgreens.com/store/deals
3. Cupones: https://www.walgreens.com/offers/offers.jsp?storeid=677
4. Shopper PR: https://www.walgreens.com/offers/offers.jsp?view=weeklyad&store_code=677

`scripts/weekly.py` usa las mismas consultas públicas sin autenticación que el JavaScript del shopper de Walgreens (`PR_WAG_DWA_0.01.js`, cargado por su web). Consulta `wag-dwa-api-prod.przone.net` con la tienda de referencia **677, Cayey**. Exige `marketVersion=PR`, catálogo publicado, periodo vigente, correspondencia de catálogo en todas las colecciones y condiciones regionales legibles. Lee las colecciones activas y elimina duplicados por identidad oficial de oferta. No es una API pública documentada con garantía de estabilidad: si cambia, el adaptador falla de forma visible y conserva datos recientes hasta 48 horas.

El shopper actual excluye #156, #217, #16409 y #21201. Estas exclusiones se extraen de sus condiciones en cada actualización; no se dan por permanentes.

El adaptador de cupones lee el estado JSON servido públicamente en el HTML. Verifica que `isPrStore=true` y la dirección de la tienda sea `PR`. Registra la tienda que realmente devolvió la página, porque el servicio puede ignorar el parámetro y devolver otra sucursal. Solo publica Walgreens IVC con canje POS; no transforma IDs en códigos promocionales y no promueve cupones nacionales de fabricante como canjeables en cajas de PR. La lectura pública no muestra la cuenta del usuario ni garantiza que pueda activar cada cupón.

`retailers.json` prepara los IDs de otras tiendas. Solo Walgreens está activo. El nuevo icono contiene Walgreens, Walmart y CVS a petición del usuario; no implica afiliación ni ofertas activas de todas esas marcas.

## Investigación del canje

La guía dentro de la app, `guide.json`, está basada en:
- Cupones y excepción expresa de PR: https://www.walgreens.com/topic/help/shophelp/coupons_help.jsp
- Política de cupones, impresos y Register Rewards: https://www.walgreens.com/topic/help/generalhelp/coupon_policy_main.jsp
- Membresía, teléfono y beneficios: https://www.walgreens.com/topic/help/generalhelp/mywalgreens-termsofuse.jsp
- Pickup: https://www.walgreens.com/topic/help/pickup.jsp
- Términos de cada promoción y del shopper PR.

No se encontró autorización pública para introducir códigos online generales en cajas de Puerto Rico. No se realizaron compras de prueba. La política general de cupones no se presenta como garantía de aceptación de cualquier cupón en PR. El sistema comprueba diariamente dos reglas clave de la ayuda oficial; si desaparecen o no se pueden leer, los cupones digitales dejan de clasificarse como verificados hasta revisión. La guía mantiene su fecha de investigación; no pretende reescribir automáticamente las políticas cuando cambian.

## Actualización y publicación

Un workflow `.github/workflows/pages.yml` prueba, consulta las cuatro fuentes y las políticas, guarda `offers.json`, prepara `dist/` y publica Pages. Corre con push a `main`, manualmente y diariamente a las **06:17 a. m. de Puerto Rico** (10:17 UTC). La publicación ocurre en el mismo workflow para no depender de que los commits del bot disparen otro workflow.

GitHub puede retrasar horarios y deshabilitar programaciones de repositorios públicos tras 60 días sin actividad. Revisar Actions y reactivar si aparece deshabilitado. Los fallos de fuente quedan visibles tanto en Actions como en la app. Solo se retienen datos revisados hace menos de 48 horas y aún vigentes. El frontend también oculta vencidas, futuras o viejas. El botón ↻ descarga el último catálogo publicado: no inicia una consulta del comercio desde el teléfono.

HTML, JS y datos usan red primero con respaldo offline. Las importaciones del catálogo llevan versión junto al JS y CSS para impedir que el navegador mezcle módulos de distintas publicaciones. El service worker elimina solo cachés de Peseteando. Los favoritos conservan la clave anterior y no se borran con las actualizaciones. La instalación y el refresco del icono en el sistema operativo dependen del navegador.

## Desarrollo y validación

Python 3.12+, Node 22+:

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -v
node --test tests/catalog.test.mjs
python scripts/refresh.py
python scripts/build.py
```

Las pruebas cubren la región, vigencia local, año y DST, deduplicación, aislamiento de promociones sin verificar, canje por canal, cupones sin código, búsqueda, favoritos y separación de recompensas frente a precios. El build solo publica archivos de la aplicación, no scripts, pruebas ni metadatos del repositorio.

Icono generado con ImageGen y exportado en 180, 192 y 512 px. El prompt pidió una composición de tarjetas de cupón con Walgreens, Walmart y CVS, una moneda de porcentaje y fondo verde oscuro; sin texto del nombre ni un teléfono de muestra.
