"""
Script de diagnóstico para verificar contraseñas en Google Sheets
"""

from services.google_sheet_service import gs_service

def diagnosticar_passwords():
    print("=" * 70)
    print("🔍 DIAGNÓSTICO DE CONTRASEÑAS EN GOOGLE SHEETS")
    print("=" * 70)
    print()
    
    try:
        # Obtener todos los usuarios
        usuarios = gs_service.get_all_records(
            book_name='credenciales',
            worksheet_name='usuarios'
        )
        
        if not usuarios:
            print("❌ No se encontraron usuarios en la hoja")
            return
        
        print(f"✅ Se encontraron {len(usuarios)} usuarios\n")
        
        # Analizar cada usuario
        for i, usuario in enumerate(usuarios, 1):
            email = usuario.get('Email', '')
            password = usuario.get('Contraseña', '')
            nombre = usuario.get('Nombres y Apellidos', '')
            estado = usuario.get('Estado', '')
            
            print(f"👤 Usuario #{i}:")
            print(f"   Nombre: {nombre}")
            print(f"   Email: '{email}'")
            print(f"   Estado: {estado}")
            print(f"   Contraseña:")
            print(f"      - Valor: '{password}'")
            print(f"      - Longitud: {len(str(password))} caracteres")
            print(f"      - Tipo: {type(password)}")
            print(f"      - Repr: {repr(password)}")
            
            # Detectar problemas comunes
            if password != str(password).strip():
                print(f"      ⚠️  TIENE ESPACIOS en blanco")
                print(f"      - Sin espacios: '{str(password).strip()}'")
            
            if isinstance(password, (int, float)):
                print(f"      ⚠️  Es un NÚMERO, no un texto")
                print(f"      - Como texto: '{str(password)}'")
            
            if '\n' in str(password) or '\r' in str(password):
                print(f"      ⚠️  Contiene saltos de línea")
            
            if not password:
                print(f"      ❌ CONTRASEÑA VACÍA")
            
            print()
        
        print("=" * 70)
        print("💡 RECOMENDACIONES:")
        print("=" * 70)
        print()
        print("1. Las contraseñas deben ser texto simple (sin espacios extra)")
        print("2. Verifica que no haya espacios al inicio o final de las celdas")
        print("3. Si la contraseña es solo números, Google Sheets puede tratarla como número")
        print("4. Para contraseñas numéricas, agrega un apóstrofe antes: '123456")
        print()
        print("🧪 PRUEBA DE LOGIN:")
        print("Intenta hacer login con estos datos exactos (copia y pega):")
        print()
        
        if len(usuarios) > 0:
            primer_usuario = usuarios[0]
            print(f"Email: {primer_usuario.get('Email', '')}")
            print(f"Contraseña: {str(primer_usuario.get('Contraseña', '')).strip()}")
        
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    diagnosticar_passwords()