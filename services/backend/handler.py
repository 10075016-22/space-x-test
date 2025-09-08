import json
import os
import time
import urllib.request
import urllib.error
import boto3
from decimal import Decimal
from typing import Any, Dict, List


def convert_decimals(obj):
    """
    Convert Decimal objects to native Python types for JSON serialization.
    """
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    else:
        return obj


def hello(event, context):
    body = {
        "message": "Go Serverless v2.0! Your function executed successfully!",
        "subtitle": "Why so serious?"
    }

    response = {"statusCode": 200, "body": json.dumps(body)}

    return response


def sync(event, context):
    table_name = os.environ.get("TABLE_NAME", "AppDataTable")
    dynamo = boto3.resource("dynamodb")
    table = dynamo.Table(table_name)

    # Query SpaceX API to get launches
    url = "https://api.spacexdata.com/v4/launches/query"
    payload = {
        "query": {},
        "options": {
            "sort": {"date_unix": "desc"},
            "limit": 100,
            "populate": ["rocket", "launchpad", "payloads"],
        },
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # Open the URL and get the response
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"statusCode": e.code, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    docs: List[Dict[str, Any]] = data.get("docs", [])
    items: List[Dict[str, Any]] = []

    for doc in docs:
        launch_id = doc.get("id")
        mission_name = doc.get("name")
        date_unix = doc.get("date_unix")
        date_utc = doc.get("date_utc")
        upcoming = doc.get("upcoming")
        success = doc.get("success")

        if upcoming:
            status = "upcoming"
        else:
            status = "success" if success else "failed"

        rocket_obj = doc.get("rocket") or {}
        rocket_name = rocket_obj.get("name") if isinstance(rocket_obj, dict) else None

        launchpad_obj = doc.get("launchpad") or {}
        launchpad_name = launchpad_obj.get("name") if isinstance(launchpad_obj, dict) else None

        payloads = doc.get("payloads") or []
        payload_names: List[str] = []
        if isinstance(payloads, list):
            for p in payloads:
                if isinstance(p, dict) and "name" in p:
                    payload_names.append(p["name"])    

        if not launch_id:
            continue

        # pk/sk model to support sort by date on queries
        pk = launch_id
        sk = str(date_unix or int(time.time()))

        item: Dict[str, Any] = {
            "pk": pk,
            "sk": sk,
            "mission_name": mission_name,
            "rocket_name": rocket_name,
            "launch_date_utc": date_utc,
            "launch_date_unix": date_unix,
            "status": status,
            "launchpad_name": launchpad_name,
        }

        if payload_names:
            item["payload_names"] = payload_names

        items.append(item)

    # Batch write to DynamoDB (upserts)
    try:
        with table.batch_writer(overwrite_by_pkeys=["pk", "sk"]) as batch:
            for item in items:
                batch.put_item(Item=item)
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": f"DynamoDB error: {str(e)}"})}

    return {
        "statusCode": 200,
        "body": json.dumps({
            "saved": len(items),
            "table": table_name,
        }),
    }


# function to get all launches
def launches(event, context):
    """
    Get all launches from the DynamoDB database.
    """
    table_name = os.environ.get("TABLE_NAME", "AppDataTable")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    try:
        # Scan the table to get all launches
        response = table.scan()
        items = response.get("Items", [])

        # If there is pagination, we continue getting the next items
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        # Convert Decimal objects to native Python types for JSON serialization
        converted_items = convert_decimals(items)
        
        return {
            "statusCode": 200,
            "body": json.dumps({"launches": converted_items}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error getting launches: {str(e)}"}),
        }

def statistics(event, context):
    """
    Get the statistics of the launches from the DynamoDB database.
    """
    table_name = os.environ.get("TABLE_NAME", "AppDataTable")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    
    try:
        # Scan the table to get all launches
        response = table.scan()
        items = response.get("Items", [])
        
        # If there is pagination, we continue getting the next items
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        # Get the statistics of the launches
        statistics = {
            "total": len(items),
            "success": sum(1 for item in items if item["status"] == "success"),
            "failed": sum(1 for item in items if item["status"] == "failed"),
            "upcoming": sum(1 for item in items if item["status"] == "upcoming"),
            "success_rate": sum(1 for item in items if item["status"] == "success") / len(items) * 100,
        }

        # Convert Decimal objects to native Python types for JSON serialization
        converted_statistics = convert_decimals(statistics)
        
        return {
            "statusCode": 200,
            "body": json.dumps(converted_statistics),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error getting statistics: {str(e)}"}),
        }

def success_rate(event, context):
    """
    Get the overall success rate of the launches from the DynamoDB database.
    """
    table_name = os.environ.get("TABLE_NAME", "AppDataTable")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    
    try:
        # Scan the table to get all launches
        response = table.scan()
        items = response.get("Items", [])
        
        # If there is pagination, we continue getting the next items
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
            
        # Get the overall success rate of the launches
        
        statistics = {
            "total_success": sum(1 for item in items if item["status"] == "success"),
            "total_failed": sum(1 for item in items if item["status"] == "failed"),
            "total_upcoming": sum(1 for item in items if item["status"] == "upcoming"),
        }
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "labels": ["Exitosos", "Fallidos", "Pendientes"],
                "statistics": [statistics["total_success"], statistics["total_failed"], statistics["total_upcoming"]]
            }),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error getting overall success rate: {str(e)}"}),
        }

def launches_by_year(event, context):
    """
    Get the launches by year from the DynamoDB database.
    """
    table_name = os.environ.get("TABLE_NAME", "AppDataTable")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    
    try:
        # Scan the table to get all launches
        response = table.scan()
        items = response.get("Items", [])
        
        # If there is pagination, we continue getting the next items
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
            
        # Get the launches by year
        from collections import defaultdict

        launches_by_year = defaultdict(int)
        for item in items:
            fecha = item.get("launch_date_utc", "")
            if len(fecha) >= 4 and fecha[:4].isdigit():
                launches_by_year[fecha[:4]] += 1

        launches_by_year = dict(launches_by_year)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "labels": list(launches_by_year.keys()),
                "statistics": list(launches_by_year.values())
            }),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error getting launches by year: {str(e)}"}),
        }

def count_rockets(event, context):
    """
    Obtener la cantidad de lanzamientos por tipo de cohete desde la base de datos DynamoDB.
    """
    table_name = os.environ.get("TABLE_NAME", "AppDataTable")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    
    try:
        # Escanear la tabla para obtener todos los lanzamientos
        response = table.scan()
        items = response.get("Items", [])
        
        # Si hay paginación, continuar obteniendo los siguientes ítems
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        
        # Contar la cantidad de lanzamientos por tipo de cohete
        from collections import defaultdict
        rocket_counts = defaultdict(int)
        for item in items:
            rocket_name = item.get("rocket_name", "Desconocido")
            rocket_counts[rocket_name] += 1

        # Preparar la respuesta
        rocket_counts = dict(rocket_counts)
        return {
            "statusCode": 200,
            "body": json.dumps({
                "labels": list(rocket_counts.keys()),
                "statistics": list(rocket_counts.values())
            }),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error al obtener la cantidad por tipo de cohete: {str(e)}"}),
        }

def swagger(event, context):
    """
    Serve Swagger UI for API documentation.
    """
    try:
        # Read the swagger.yaml file
        with open('swagger.yaml', 'r', encoding='utf-8') as file:
            swagger_content = file.read()
        
        # Return the swagger.yaml content
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/x-yaml",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "GET, OPTIONS"
            },
            "body": swagger_content
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error serving swagger: {str(e)}"}),
        }


def swagger_ui(event, context):
    """
    Serve Swagger UI HTML page.
    """
    try:
        # Simple HTML with inline Swagger spec
        html_content = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpaceX API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
    <style>
        html {
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }
        *, *:before, *:after {
            box-sizing: inherit;
        }
        body {
            margin:0;
            background: #fafafa;
        }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: window.location.origin + '/swagger',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                validatorUrl: null
            });
        };
    </script>
</body>
</html>
"""
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/html",
                "Access-Control-Allow-Origin": "*"
            },
            "body": html_content
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error serving swagger UI: {str(e)}"}),
        }
