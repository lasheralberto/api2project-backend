import os
from flask import Flask, request, jsonify, render_template_string
import stripe
from datetime import datetime, timedelta
import json
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Configuración de Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simulación de base de datos en memoria (en producción usar una DB real)
users_db = {}
subscriptions_db = {}

# Planes disponibles (similar a tu estructura)
PLANS = {
    'free': {
        'name': 'Free',
        'operations_max_daily': 1,
        'price': 0
    },
    'amateur': {
        'name': 'Amateur',
        'operations_max_daily': 3,
        'price': 3,
        'stripe_price_id': 'price_amateur_monthly'  # Reemplaza con tu Price ID real
    },
    'pro': {
        'name': 'Pro',
        'operations_max_daily': 12,
        'price': 10,
        'stripe_price_id': 'price_pro_monthly'  # Reemplaza con tu Price ID real
    }
}

def get_user_subscription_status(user_id):
    """Obtiene el estado de suscripción del usuario"""
    user = users_db.get(user_id)
    if not user:
        return {'plan': 'free', 'active': False, 'operations_today': 0}
    
    # Verificar si es el mismo día
    today = datetime.now().strftime('%Y-%m-%d')
    if user.get('last_operation_date') != today:
        user['operations_today'] = 0
        user['last_operation_date'] = today
    
    return {
        'plan': user.get('plan', 'free'),
        'active': user.get('subscription_active', False),
        'operations_today': user.get('operations_today', 0),
        'operations_max_daily': PLANS[user.get('plan', 'free')]['operations_max_daily'],
        'stripe_customer_id': user.get('stripe_customer_id'),
        'stripe_subscription_id': user.get('stripe_subscription_id')
    }

def can_user_operate(user_id):
    """Verifica si el usuario puede realizar una operación"""
    status = get_user_subscription_status(user_id)
    return status['operations_today'] < status['operations_max_daily']

def register_user_operation(user_id):
    """Registra una operación del usuario"""
    if user_id not in users_db:
        users_db[user_id] = {
            'plan': 'free',
            'subscription_active': False,
            'operations_today': 0,
            'last_operation_date': datetime.now().strftime('%Y-%m-%d')
        }
    
    today = datetime.now().strftime('%Y-%m-%d')
    user = users_db[user_id]
    
    if user.get('last_operation_date') != today:
        user['operations_today'] = 0
        user['last_operation_date'] = today
    
    user['operations_today'] += 1
    logger.info(f"User {user_id} performed operation. Total today: {user['operations_today']}")

@app.route('/')
def index():
    """Página principal con información de la API"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stripe Subscription Checker</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .endpoint { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }
            .method { color: #007bff; font-weight: bold; }
            .plans { display: flex; gap: 20px; margin: 20px 0; }
            .plan { border: 2px solid #ddd; padding: 20px; border-radius: 10px; text-align: center; flex: 1; }
            .plan.amateur { border-color: #ffc107; }
            .plan.pro { border-color: #28a745; }
            code { background: #f8f9fa; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Stripe Subscription Checker API</h1>
            <p>API sencilla para verificar suscripciones de Stripe basada en tu app React.</p>
            
            <h2>📊 Planes Disponibles</h2>
            <div class="plans">
                <div class="plan">
                    <h3>Free</h3>
                    <p>1 operación/día</p>
                    <p><strong>€0/mes</strong></p>
                </div>
                <div class="plan amateur">
                    <h3>Amateur</h3>
                    <p>3 operaciones/día</p>
                    <p><strong>€3/mes</strong></p>
                </div>
                <div class="plan pro">
                    <h3>Pro</h3>
                    <p>12 operaciones/día</p>
                    <p><strong>€10/mes</strong></p>
                </div>
            </div>
            
            <h2>🔌 Endpoints Disponibles</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/user/&lt;user_id&gt;/status</code>
                <p>Obtiene el estado de suscripción del usuario</p>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/api/user/&lt;user_id&gt;/check-operation</code>
                <p>Verifica si el usuario puede realizar una operación</p>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/api/user/&lt;user_id&gt;/register-operation</code>
                <p>Registra una operación del usuario</p>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/api/create-checkout-session</code>
                <p>Crea una sesión de pago de Stripe</p>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/api/webhook/stripe</code>
                <p>Webhook para manejar eventos de Stripe</p>
            </div>
            
            <h2>🧪 Probar la API</h2>
            <p>Ejemplos de uso:</p>
            <pre><code>curl -X GET "http://localhost:5000/api/user/user123/status"
curl -X POST "http://localhost:5000/api/user/user123/check-operation"
curl -X POST "http://localhost:5000/api/user/user123/register-operation"</code></pre>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/api/user/<user_id>/status', methods=['GET'])
def get_user_status(user_id):
    """Obtiene el estado completo del usuario"""
    try:
        status = get_user_subscription_status(user_id)
        return jsonify({
            'success': True,
            'user_id': user_id,
            'status': status
        })
    except Exception as e:
        logger.error(f"Error getting user status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user/<user_id>/check-operation', methods=['POST'])
def check_user_operation(user_id):
    """Verifica si el usuario puede realizar una operación"""
    try:
        can_operate = can_user_operate(user_id)
        status = get_user_subscription_status(user_id)
        
        return jsonify({
            'success': True,
            'can_operate': can_operate,
            'user_id': user_id,
            'operations_today': status['operations_today'],
            'operations_max_daily': status['operations_max_daily'],
            'plan': status['plan']
        })
    except Exception as e:
        logger.error(f"Error checking user operation: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user/<user_id>/register-operation', methods=['POST'])
def register_operation(user_id):
    """Registra una operación del usuario"""
    try:
        if not can_user_operate(user_id):
            return jsonify({
                'success': False,
                'error': 'Daily operation limit reached',
                'message': 'Has alcanzado el límite de operaciones diarias.'
            }), 403
        
        register_user_operation(user_id)
        status = get_user_subscription_status(user_id)
        
        return jsonify({
            'success': True,
            'message': 'Operation registered successfully',
            'operations_today': status['operations_today'],
            'operations_remaining': status['operations_max_daily'] - status['operations_today']
        })
    except Exception as e:
        logger.error(f"Error registering operation: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Crea una sesión de checkout de Stripe"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        plan = data.get('plan')
        
        if not user_id or not plan or plan not in PLANS:
            return jsonify({'success': False, 'error': 'Invalid user_id or plan'}), 400
        
        if plan == 'free':
            return jsonify({'success': False, 'error': 'Cannot create session for free plan'}), 400
        
        # Crear customer en Stripe si no existe
        customer = None
        if user_id in users_db and users_db[user_id].get('stripe_customer_id'):
            customer_id = users_db[user_id]['stripe_customer_id']
            customer = stripe.Customer.retrieve(customer_id)
        else:
            customer = stripe.Customer.create(
                metadata={'user_id': user_id}
            )
            # Guardar customer_id en la base de datos
            if user_id not in users_db:
                users_db[user_id] = {}
            users_db[user_id]['stripe_customer_id'] = customer.id
        
        # Crear sesión de checkout
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': PLANS[plan]['stripe_price_id'],
                'quantity': 1,
            }],
            mode='subscription',
            customer=customer.id,
            success_url=request.url_root + 'success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.url_root + 'cancel',
            metadata={
                'user_id': user_id,
                'plan': plan
            }
        )
        
        return jsonify({
            'success': True,
            'checkout_url': session.url,
            'session_id': session.id
        })
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Webhook para manejar eventos de Stripe"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # En producción, usar el endpoint secret real
        endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        if endpoint_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        else:
            # Para desarrollo, parsear directamente
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
        
        # Manejar diferentes tipos de eventos
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session['metadata']['user_id']
            plan = session['metadata']['plan']
            
            # Actualizar usuario con suscripción activa
            if user_id not in users_db:
                users_db[user_id] = {}
            
            users_db[user_id].update({
                'plan': plan,
                'subscription_active': True,
                'stripe_customer_id': session['customer'],
                'stripe_subscription_id': session['subscription'],
                'payment_failed': False
            })
            
            logger.info(f"User {user_id} subscribed to {plan} plan")
            
        if event['type'] == 'checkout.session.async_payment_failed':
            session = event['data']['object']
            user_id = session['metadata']['user_id']
            plan = session['metadata']['plan']
            
            # Actualizar usuario con suscripción activa
            if user_id not in users_db:
                users_db[user_id] = {}
            
            users_db[user_id].update({
                'plan': plan,
                'subscription_active': True,
                'stripe_customer_id': session['customer'],
                'stripe_subscription_id': session['subscription'],
                'payment_failed': True
            })

        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/success')
def success():
    """Página de éxito después del pago"""
    return render_template_string("""
    <html>
    <head><title>¡Suscripción Exitosa!</title></head>
    <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
        <h1>🎉 ¡Suscripción Exitosa!</h1>
        <p>Tu suscripción ha sido activada correctamente.</p>
        <p>Ya puedes disfrutar de tu nuevo plan.</p>
        <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Volver al inicio</a>
    </body>
    </html>
    """)

@app.route('/cancel')
def cancel():
    """Página de cancelación"""
    return render_template_string("""
    <html>
    <head><title>Suscripción Cancelada</title></head>
    <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
        <h1>❌ Suscripción Cancelada</h1>
        <p>No se ha procesado ningún pago.</p>
        <p>Puedes intentarlo de nuevo cuando quieras.</p>
        <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Volver al inicio</a>
    </body>
    </html>
    """)

# Endpoint para testing - crear usuarios de prueba
@app.route('/api/test/create-users', methods=['POST'])
def create_test_users():
    """Crea usuarios de prueba para testing"""
    test_users = {
        'user_free': {'plan': 'free', 'subscription_active': False, 'operations_today': 0},
        'user_amateur': {'plan': 'amateur', 'subscription_active': True, 'operations_today': 1},
        'user_pro': {'plan': 'pro', 'subscription_active': True, 'operations_today': 5}
    }
    
    for user_id, data in test_users.items():
        users_db[user_id] = {
            **data,
            'last_operation_date': datetime.now().strftime('%Y-%m-%d')
        }
    
    return jsonify({
        'success': True,
        'message': 'Test users created',
        'users': list(test_users.keys())
    })

if __name__ == '__main__':
    # Verificar que las variables de entorno estén configuradas
    if not stripe.api_key:
        print("⚠️  ADVERTENCIA: STRIPE_SECRET_KEY no está configurada")
        print("   Configura la variable de entorno STRIPE_SECRET_KEY")
    
    print("🚀 Iniciando Flask Stripe Subscription Checker")
    print("📋 Endpoints disponibles:")
    print("   GET  /                                  - Página principal")
    print("   GET  /api/user/<id>/status             - Estado del usuario")
    print("   POST /api/user/<id>/check-operation    - Verificar operación")
    print("   POST /api/user/<id>/register-operation - Registrar operación")
    print("   POST /api/create-checkout-session      - Crear sesión de pago")
    print("   POST /api/webhook/stripe               - Webhook de Stripe")
    print("   POST /api/test/create-users            - Crear usuarios de prueba")
    print("")
    print("🧪 Para probar, ejecuta:")
    print("   curl -X POST 'http://localhost:5000/api/test/create-users'")
    print("   curl -X GET 'http://localhost:5000/api/user/user_free/status'")
    
    app.run(debug=True, host='0.0.0.0', port=5000)