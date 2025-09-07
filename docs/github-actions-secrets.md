# Configurar secretos de GitHub Actions para CDK Deploy

## Dónde agregarlos
- En GitHub: Settings → Secrets and variables → Actions → New repository secret

## Secretos requeridos (recomendado: OIDC)
- AWS_ROLE_TO_ASSUME: ARN del rol IAM a asumir por GitHub Actions (OIDC)
- AWS_REGION: Región AWS destino (ej. us-east-1)

El workflow referencia estos secretos:

```yaml
# .github/workflows/cdk-deploy.yml
with:
  role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
  aws-region: ${{ secrets.AWS_REGION }}
```

## Crear el rol OIDC en AWS (resumen)
1. Proveedor OIDC: token.actions.githubusercontent.com
2. Rol IAM con confianza al proveedor y al repo/branch. Usa como base `docs/iam-trust-policy-oidc.json` (reemplaza `<ACCOUNT_ID>`, `ORG/REPO`).

3. Permisos mínimos del rol para CDK deploy: usa `docs/iam-permissions-policy-cdk-deploy.json` como política administrada o inline.

## Alternativa con claves estáticas (menos segura)
- AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY y AWS_REGION.
- Cambia el paso de credenciales en el workflow a:

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: ${{ secrets.AWS_REGION }}
```

## Verificación
- Ejecuta el workflow (push a main o manual) y revisa que corran `cdk bootstrap` y `cdk deploy` sin pedir aprobación.
