# Peseteando PR

PWA de códigos de descuento para iPhone y Android. Catálogo, copia de códigos, categorías, búsqueda, ordenación y favoritos locales. Sin cuenta, Supabase ni APIs de pago.

**App:** https://fravier3.github.io/Peseteando/

## Datos y Puerto Rico

Fuentes públicas oficiales:
- https://www.walgreens.com/promotion/offer-details
- https://photo.walgreens.com/store/deals

Solo se extraen códigos promocionales literales con descuento y vencimiento explícitos. No se convierten IDs de cupones en códigos. Se excluyen términos que indiquen que no aplica en Puerto Rico. **La ausencia de exclusión no demuestra aceptación en PR:** todos los códigos se identifican como «Confirmar en PR» hasta que se prueben en un carrito con tienda/dirección de PR. No se ha realizado esa comprobación. Las fechas se interpretan con la zona America/Chicago y se presentan en hora de Puerto Rico. Se exige año explícito; nunca se renueva un código vencido cambiando el año.

Se guardan códigos, nombres, descuento, compra mínima detectable, condiciones resumidas, imagen cuando la fuente la publica, URL, fecha de revisión y hash de evidencia. Los términos completos se consultan en Walgreens. Las fotos son del servicio promocionado; los códigos generales usan una ilustración de compra, no una foto de un producto concreto. El importador no interpreta todas las condiciones posibles: antes de comprar, consultar los términos enlazados.

## Actualización y publicación

Un único workflow `.github/workflows/pages.yml` prueba, consulta las dos fuentes, guarda `offers.json`, prepara `dist/` y lo publica en Pages. Corre al hacer push, manualmente y a las **06:17 a. m. de Puerto Rico** (10:17 UTC). El mismo workflow publica el JSON actualizado, sin depender de que un commit del bot active otro workflow.

GitHub puede retrasar los horarios y desactivar los workflows programados de repositorios públicos después de 60 días sin actividad. Revisar Actions; reactivar el workflow y ejecutarlo manualmente si aparece deshabilitado. La automatización cubre estas dos páginas, no toda la web ni todos los códigos posibles.

Si una fuente falla o no hay promociones legibles, el workflow avisa y el sitio publica el estado. Solo retiene datos revisados en las últimas 48 horas que siguen vigentes. El frontend también oculta códigos vencidos o sin revisión reciente, incluso sin nueva publicación. «Actualizar» descarga el último catálogo publicado; no inicia un raspado desde el teléfono.

No requiere reinstalar la PWA: HTML, JS y datos usan red primero. El service worker usa caché solo como respaldo sin conexión. Los favoritos no se borran con las actualizaciones.

## Desarrollo

Python 3.12+, Node 22+:

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -v
node --test tests/catalog.test.mjs
python scripts/refresh.py
python scripts/build.py
```

Para añadir fuentes o corregir un código: editar el importador y sus pruebas, verificar las condiciones originales y hacer push. Evitar editar `offers.json` manualmente: el siguiente refresco lo reemplaza. Antes de incorporar otra tienda, validar un origen público automatizable y su cobertura para PR.

## Verificaciones

Las pruebas cubren extracción de códigos, fechas y cambio de año, DST, exclusión de PR, deduplicación, búsqueda, favoritos y descarte de datos viejos. El workflow conserva evidencia de sus ejecuciones. Las pruebas de instalación nativa y canje real deben realizarse en los dispositivos y en Walgreens; no se presentan como efectuadas.
