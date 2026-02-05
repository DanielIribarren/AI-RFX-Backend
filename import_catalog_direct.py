"""
Script para importar catálogo directamente a la BD
Sin necesidad de servidor corriendo
"""
import os
import csv
from dotenv import load_dotenv
from supabase import create_client
from decimal import Decimal

# Cargar variables de entorno
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

print("=" * 80)
print("📦 IMPORTACIÓN DIRECTA DE CATÁLOGO")
print("=" * 80)

# Conectar a Supabase
client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Obtener organización
print("\n🏢 Obteniendo organización...")
orgs = client.table("organizations").select("id, name").limit(1).execute()

if not orgs.data:
    print("❌ No hay organizaciones en la BD")
    exit(1)

org_id = orgs.data[0]['id']
org_name = orgs.data[0]['name']
print(f"✅ Organización: {org_name} ({org_id})")

# Leer CSV
csv_file = "examples/catalog_example.csv"
print(f"\n📁 Leyendo archivo: {csv_file}")

products = []
with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Mapear columnas
        product = {
            'organization_id': org_id,
            'product_name': row['Nombre del Producto'],
            'product_code': row['Código'],
            'unit_cost': float(row['Costo Unitario'].replace(',', '.')),
            'unit_price': float(row['Precio Unitario'].replace(',', '.')),
            'unit': row['Unidad'],
            'is_active': True
        }
        products.append(product)

print(f"✅ Leídos {len(products)} productos")

# Insertar en BD (batch de 50)
print(f"\n💾 Insertando productos en BD...")
batch_size = 50
total_inserted = 0

for i in range(0, len(products), batch_size):
    batch = products[i:i+batch_size]
    try:
        result = client.table("product_catalog").insert(batch).execute()
        total_inserted += len(batch)
        print(f"   ✅ Insertados {total_inserted}/{len(products)} productos")
    except Exception as e:
        print(f"   ❌ Error en batch {i//batch_size + 1}: {e}")

print(f"\n✅ IMPORTACIÓN COMPLETADA: {total_inserted} productos")

# Verificar
print("\n🔍 Verificando productos insertados...")
result = client.table("product_catalog")\
    .select("id, product_name, unit_price")\
    .eq("organization_id", org_id)\
    .limit(5)\
    .execute()

print(f"✅ Productos en BD: {len(result.data)}")
print("\nPrimeros 5 productos:")
for p in result.data:
    print(f"   - {p['product_name']}: ${p['unit_price']}")

print("\n" + "=" * 80)
print("✅ CATÁLOGO IMPORTADO EXITOSAMENTE")
print("=" * 80)
print("\n📝 AHORA PUEDES:")
print("   1. Ejecutar: python test_catalog_simple.py")
print("   2. O iniciar servidor: python backend/app.py")
print("   3. Y probar: GET /api/catalog/search?query=tequeños")
print("=" * 80)
