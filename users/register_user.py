import boto3, time, os, hashlib, json

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def notify_new_user(user):
    sns = boto3.client('sns')
    topic_arn = os.environ['USER_REGISTER_TOPIC']

    message = {
        'event': 'new_user_registered',
        'user_id': user['user_id'],
        'type': user['type']
    }

    sns.publish(
        TopicArn=topic_arn,
        Message=json.dumps(message),
        Subject=f"Nuevo usuario registrado: {user['user_id']}"
    )

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table_name = os.environ['users_table']
    admin_key = os.environ['ADMIN_MASTER_KEY']
    table = dynamodb.Table(table_name)
    now = str(time.time())

    body = event.get("body")
    if isinstance(body, str):
        body = json.loads(body)

    # Validaciones
    user_type = body.get('type', '').lower()
    if user_type not in ['admin', 'user', 'solver']:
        return {'statusCode': 400, 'body': 'Invalid type'}

    if user_type == 'admin' and body.get('admin_key') != admin_key:
        return {'statusCode': 403, 'body': 'Invalid admin key'}

    user_id = body.get('user_id', '')
    if "@utec.edu.pe" not in user_id:
        return {'statusCode': 400, 'body': 'Invalid user_id'}

    password = body.get('password', '')
    if len(password) < 6:
        return {'statusCode': 400, 'body': 'Password too short'}

    name = body.get('name', '').strip()
    if not name or not all(c.isalpha() or c.isspace() for c in name):
        return {'statusCode': 400, 'body': 'Invalid name'}

    # Verificar si ya existe
    existing_user = table.get_item(Key={'type': user_type, 'user_id': user_id})
    if 'Item' in existing_user:
        return {'statusCode': 409, 'body': 'User already exists'}

    # Crear registro
    user_item = {
        'user_id': user_id,
        'name': name,
        'type': user_type,
        'password_hash': hash_password(password),
        'active': True,
        'created_at': now,
        'updated_at': now
    }

    try:
        table.put_item(Item=user_item)

        notify_new_user(user_item)

        return {
            'statusCode': 201,
            'body': json.dumps({'message': f'User {user_id} created successfully'})
        }

    except Exception as e:
        return {'statusCode': 500, 'body': f'Error creating user: {str(e)}'}
