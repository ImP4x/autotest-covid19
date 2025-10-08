import os
import uuid
from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Configuración de base de datos
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    """Inicializa la tabla si no existe"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS resultados_covid (
                id SERIAL PRIMARY KEY,
                usuario_id VARCHAR(100) UNIQUE NOT NULL,
                diagnostico TEXT NOT NULL,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()
        print("Tabla creada exitosamente")
    except Exception as e:
        print(f"Error al inicializar DB: {e}")

@app.route('/')
def index():
    # Inicializar base de datos al cargar la página
    init_db()
    # Generar ID aleatorio para el usuario
    usuario_id = str(uuid.uuid4())
    return render_template('index.html', usuario_id=usuario_id)

@app.route('/evaluar', methods=['POST'])
def evaluar():
    try:
        data = request.get_json()
        usuario_id = data.get('usuario_id')
        pregunta1 = data.get('pregunta1')  # Contacto COVID
        pregunta2 = data.get('pregunta2')  # Presenta síntomas
        pregunta3 = data.get('pregunta3', None)  # Más de 14 días
        pregunta4 = data.get('pregunta4', None)  # Dificultad respiratoria
        
        # Lógica de negocio según las reglas
        diagnostico = ""
        mostrar_pregunta3 = False
        mostrar_pregunta4 = False
        
        # Regla a: Si pregunta 1 y 2 son NO
        if pregunta1 == 'NO' and pregunta2 == 'NO':
            diagnostico = "En este momento su situación no requiere asistencia médica."
        
        # Si solo pregunta 1 es SI y pregunta 2 es NO
        elif pregunta1 == 'SI' and pregunta2 == 'NO':
            diagnostico = "En este momento su situación no requiere asistencia médica."
        
        # Si pregunta 1 es NO y pregunta 2 es SI
        elif pregunta1 == 'NO' and pregunta2 == 'SI':
            diagnostico = "En este momento su situación no requiere asistencia médica."
        
        # Regla b: Si pregunta 1 y 2 son SI, desplegar pregunta 3
        elif pregunta1 == 'SI' and pregunta2 == 'SI':
            if pregunta3 is None:
                mostrar_pregunta3 = True
            else:
                # Regla d: Si pregunta 3 es SI
                if pregunta3 == 'SI':
                    diagnostico = "La COVID-19 se presenta como una enfermedad aguda, por lo tanto, los síntomas que presenta en este momento podrían deberse a otra causa diferente del nuevo coronavirus."
                
                # Regla c: Si pregunta 3 es NO, desplegar pregunta 4
                elif pregunta3 == 'NO':
                    if pregunta4 is None:
                        mostrar_pregunta4 = True
                    else:
                        # Regla e: Si pregunta 4 es SI
                        if pregunta4 == 'SI':
                            diagnostico = "Sus síntomas parecen indicar gravedad"
                        
                        # Regla f: Si pregunta 4 es NO
                        elif pregunta4 == 'NO':
                            diagnostico = "Llame al número 01-8000-66666 pida una consulta telefónica con su centro de salud, indicando los síntomas que presenta y que tuvo un contacto estrecho con un caso de COVID-19."
        
        # Guardar en base de datos si hay diagnóstico final
        if diagnostico and usuario_id:
            guardar_resultado(usuario_id, diagnostico)
        
        return jsonify({
            'diagnostico': diagnostico,
            'mostrar_pregunta3': mostrar_pregunta3,
            'mostrar_pregunta4': mostrar_pregunta4
        })
    
    except Exception as e:
        print(f"Error en evaluar: {e}")
        return jsonify({'error': str(e)}), 500

def guardar_resultado(usuario_id, diagnostico):
    """Guarda el resultado en la base de datos"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO resultados_covid (usuario_id, diagnostico) VALUES (%s, %s) ON CONFLICT (usuario_id) DO UPDATE SET diagnostico = %s',
            (usuario_id, diagnostico, diagnostico)
        )
        conn.commit()
        cur.close()
        conn.close()
        print(f"Resultado guardado para usuario {usuario_id}")
    except Exception as e:
        print(f"Error al guardar resultado: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
