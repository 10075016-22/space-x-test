# Backend - Guía de uso, configuración local y despliegue

## Resumen
- Runtime: Python 3.11 (Serverless Framework v3)
- Endpoints (HTTP API):
  - POST `/sync`: consulta SpaceX v4 (`/launches/query`) y persiste lanzamientos en DynamoDB.
- Persistencia: tabla DynamoDB con claves `pk` (launch_id) y `sk` (date_unix).
- Campos guardados: `mission_name`, `rocket_name`, `launch_date_utc`, `launch_date_unix`, `status` (success/failed/upcoming), `launchpad_name`, `payload_names`.

## Estructura
- Código: `services/backend/handler.py`
- Config: `services/backend/serverless.yml`
- Tests: `services/backend/tests/`

## Variables de entorno
- `TABLE_NAME` (obligatoria): nombre de la tabla DynamoDB (ej. `space-x-launches`).
  - Se carga desde `services/backend/.env` (Serverless `useDotenv: true`).

## Configuración local
1) Requisitos
- Python 3.11, Node 20, AWS CLI con credenciales válidas.

2) Instalar dependencias y preparar entorno
```bash
cd services/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3) Configurar `.env`
```bash
# services/backend/.env
TABLE_NAME=space-x-launches
```
Asegúrate de que la tabla exista en AWS (creada por CDK) o ajusta el nombre.

4) Ejecutar offline (usa AWS real para DynamoDB)
```bash
# Desde la raíz del repo (activa .venv automáticamente en el script)
npm run offline
# En otra terminal
curl -X POST http://localhost:3000/sync
```
Notas:
- Se conecta a DynamoDB de tu cuenta AWS (no local). Exporta tu perfil/región si aplica:
```bash
export AWS_PROFILE=<tu_perfil>
export AWS_REGION=<tu_region>
```

## Pruebas unitarias
```bash
cd services/backend
source .venv/bin/activate
pytest -q
```
Cobertura actual:
- Camino feliz `/sync` con mocks de SpaceX y DynamoDB.
- Errores de llamada SpaceX.

## Despliegue manual
```bash
cd services/backend
npx serverless@3 deploy --stage prod
```
- Envía `TABLE_NAME` desde `.env`.

## Despliegue CI/CD (GitHub Actions)
Workflow: `.github/workflows/backend-deploy.yml`
- Ejecuta tests y luego despliega con Serverless usando OIDC.
- Secretos necesarios (en GitHub: Settings → Secrets and variables → Actions):
  - `AWS_ROLE_TO_ASSUME`: ARN del rol con confianza OIDC y permisos de deploy.
  - `AWS_REGION`: región destino (ej. `us-east-1`).
  - `TABLE_NAME`: nombre de la tabla (ej. `space-x-launches`).

## Modelo de datos (DynamoDB)
- Partición: `pk = <launch_id>`
- Ordenamiento: `sk = <date_unix>`
- Atributos principales:
  - `mission_name`, `rocket_name`, `launch_date_utc`, `launch_date_unix`, `status`, `launchpad_name`, `payload_names` (lista)

## Troubleshooting
- `ModuleNotFoundError: boto3`: activa `.venv` e instala `requirements.txt`.
- Offline no escribe en Dynamo: verifica credenciales AWS, `AWS_PROFILE`, `AWS_REGION` y `TABLE_NAME`.
- 403/permiso denegado: revisa políticas IAM del rol Lambda y/o del usuario local.
