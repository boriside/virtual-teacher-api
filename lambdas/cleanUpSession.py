import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('session')


def lambda_handler(event, context):
    session_id = event['queryStringParameters']['id']
    response = table.delete_item(Key={'id': session_id})

    return {
        'statusCode': 200,
        'body': json.dumps('Deleted session: ' + session_id)
    }
