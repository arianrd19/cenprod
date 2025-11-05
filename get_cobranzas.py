"""
Script de diagnóstico para verificar datos de cobranza en Google Sheets
"""
from services.google_sheet_service import gs_service
from datetime import datetime, timedelta

def diagnosticar_cobranzas():
    print("=" * 70)
    print("🔍 DIAGNÓSTICO DE COBRANZAS EN GOOGLE SHEETS")
    print("=" * 70)
    print()

    try:
        # Obtener todos los registros de la hoja de ventas (usada para cobranzas)
        print("📊 Obteniendo registros de la hoja de ventas (QUERYS)...")
        records = gs_service.get_all_records(book_name='ventas', worksheet_name='registro')

        if not records:
            print("❌ No se encontraron registros en la hoja de ventas (QUERYS)")
            return

        print(f"✅ Se encontraron {len(records)} registros")
        print(f"📋 Encabezados: {list(records[0].keys())}")
        print()

        # Filtrar registros con diferencias en los montos
        registros_con_diferencias = []
        for record in records:
            try:
                monto_total = gs_service._safe_float(record.get('MONTO TOTAL DE LA VENTA', 0))
                monto_depositado = gs_service._safe_float(record.get('MONTO DEPOSITADO', 0))

                if monto_total != monto_depositado:
                    fecha_venta = record.get('FECHA DE LA VENTA', '')
                    fecha_parsed = gs_service._parse_date(fecha_venta)
                    fecha_de_cobro = fecha_parsed + timedelta(days=30) if fecha_parsed else None

                    registros_con_diferencias.append({
                        'PERSONAL': record.get('PERSONAL', ''),
                        'NOMBRE COMPLETO DEL CLIENTE': record.get('NOMBRE COMPLETO DEL CLIENTE', ''),
                        'FECHA DE LA VENTA': fecha_venta,
                        'FECHA DE COBRO': fecha_de_cobro.strftime("%d/%m/%Y") if fecha_de_cobro else '',
                        'MONTO TOTAL DE LA VENTA': monto_total,
                        'MONTO DEPOSITADO': monto_depositado,
                        'DIFERENCIA': monto_total - monto_depositado,
                        'DNI DEL CLIENTE': record.get('DNI DEL CLIENTE', ''),
                        'CELULAR DEL CLIENTE': record.get('CELULAR DEL CLIENTE', ''),
                        'ESPECIALIDAD': record.get('ESPECIALIDAD', ''),
                        'OBSERVACIONES': record.get('OBSERVACIONES', '')
                    })
            except Exception as e:
                print(f"⚠️ Error procesando un registro: {e}")

        print(f"🔎 Se encontraron {len(registros_con_diferencias)} registros con diferencias en los montos")
        print()

        if registros_con_diferencias:
            print("📋 Registros con diferencias:")
            print("-" * 120)
            print(f"{'PERSONAL':<20} {'CLIENTE':<30} {'FECHA VENTA':<12} {'FECHA COBRO':<12} {'MONTO TOTAL':<12} {'MONTO DEPOSITADO':<15} {'DIFERENCIA':<10} {'DNI':<12} {'CELULAR':<15}")
            print("-" * 120)

            for registro in registros_con_diferencias:
                print(f"{registro['PERSONAL'][:20]:<20} {registro['NOMBRE COMPLETO DEL CLIENTE'][:30]:<30} {registro['FECHA DE LA VENTA']:<12} {registro['FECHA DE COBRO']:<12} {registro['MONTO TOTAL DE LA VENTA']:<12.2f} {registro['MONTO DEPOSITADO']:<15.2f} {registro['DIFERENCIA']:<10.2f} {registro['DNI DEL CLIENTE']:<12} {registro['CELULAR DEL CLIENTE']:<15}")

            print()
            print("=" * 70)
            print("💡 RECOMENDACIONES:")
            print("=" * 70)
            print()
            print("1. Verifica que los montos totales y depositados sean correctos.")
            print("2. Asegúrate de que las fechas de venta sean válidas.")
            print("3. Revisa que los códigos de PERSONAL coincidan con los de tus asesores.")
        else:
            print("ℹ️ No se encontraron registros con diferencias en los montos.")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    diagnosticar_cobranzas()
