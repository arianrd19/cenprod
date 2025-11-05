"""
Script de diagnóstico para verificar datos en Google Sheets
"""
from services.google_sheet_service import gs_service, Config
from datetime import datetime

def diagnosticar_hojas():
    print("=" * 70)
    print("🔍 DIAGNÓSTICO DE DATOS EN GOOGLE SHEETS")
    print("=" * 70)
    print()

    try:
        # Obtener configuración de hojas desde Config
        sheets_config = Config.SHEETS
        print(f"📄 Hojas configuradas: {list(sheets_config.keys())}")
        print()

        # Diagnosticar cada hoja
        for sheet_name, sheet_config in sheets_config.items():
            print(f"📊 Hoja: {sheet_name}")
            print(f"   ID: {sheet_config.get('id')}")
            print(f"   Pestañas: {list(sheet_config.get('worksheets', {}).keys())}")
            print()

            # Diagnosticar cada pestaña
            for worksheet_key, worksheet_name in sheet_config.get('worksheets', {}).items():
                print(f"   📑 Pestaña: {worksheet_name}")

                # Obtener registros
                records = gs_service.get_all_records(book_name=sheet_name, worksheet_name=worksheet_key)

                if not records:
                    print(f"      ❌ No se encontraron registros")
                    continue

                print(f"      ✅ Se encontraron {len(records)} registros")
                print(f"      📋 Encabezados: {list(records[0].keys()) if records else 'Ninguno'}")
                print()

                # Mostrar algunos registros de ejemplo
                for i, record in enumerate(records[:3], 1):
                    print(f"      📄 Registro #{i}:")
                    for key, value in record.items():
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        print(f"         {key}: {repr(value)[:100]}")
                    print()

                print("-" * 70)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    diagnosticar_hojas()
