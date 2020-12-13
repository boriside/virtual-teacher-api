import json
import boto3
from random import randint
from num2words import num2words
import requests


def get_user_session(session_id):
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('session')
        response = table.get_item(Key={'id': session_id})
        return response['Item']
    except:
        return None


def get_connection_id(device_id):
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('connections')
        response = table.get_item(Key={'id': device_id})['Item']
        print("**** ConnectionId = " + str(response))
        return response
    except Exception as e:
        print(str(e))


def store_to_db(session_obj, table_name='session'):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    response = table.put_item(
        Item=session_obj
    )
    return response

ALGEBRA = 'algebra'
SHAPE = 'geometrie'

def lambda_handler(event, context):
    # TODO implement

    session_id = event['queryStringParameters']['id']
    answer = event['queryStringParameters']['stt'].lower()
    # device_id = event['queryStringParameters']['device_id']

    # answer = 'Algebra'
    # session_id = "new_id1234"
    device_id = 'new_id1234'

    session = get_user_session(session_id)
    if not session:
        session = get_session_obj(session_id, '', answer, None, 0, None, )
        store_to_db(session)

    if answer in ['wechsel', 'wechseln'] and session:
        if session['game_type'] == ALGEBRA:
            session['game_type'] = SHAPE
        else:
            session['game_type'] = ALGEBRA
        session['attempts'] = 0

    if answer == 'algebra' or (session and session['game_type'] == ALGEBRA):
        game = NumberGame(session)
    elif answer ==  SHAPE or (session and session['game_type'] == SHAPE):
        game = ShapeGame(session)
    else:
        return {
        'statusCode': 200,
        'body': json.dumps('Entschuldigung, ich habe es nicht verstanden. Bitte wählen Sie zwischen Algebra oder Geometrie')
     }

    if not session or session['attempts'] == 0:
        question, expression = game.get_question()
    else:
        question, expression = game.check_answer(answer)

    try:
        client = boto3.client('apigatewaymanagementapi',
                              endpoint_url="https://4e2dbjjjpg.execute-api.eu-west-1.amazonaws.com/production")
        connection_id = get_connection_id(device_id)['connection_id']
        response = client.post_to_connection(
            Data=json.dumps(expression),
            ConnectionId=connection_id
        )
    except Exception as e:
        print("**** Exception" + str(e))
    return {
        'statusCode': 200,
        'body': json.dumps(question)
    }


def get_session_obj(id, question, game_type, expected, attempts, expression):
    return {
        'id': id,
        'question': question,
        'game_type': game_type,
        'expected': expected,
        'attempts': attempts,
        'expression': expression
    }


class Game:

    def __init__(self, session):
        self.session = session
        session['game_type'] = self.type
        store_to_db(session)

    def _curate_question(self):
        pass

    def get_question(self):
        question, expected, expression = self._curate_question()
        session_obj = get_session_obj(self.session['id'], question, self.session['game_type'], expected, 1,
                                      expression)
        store_to_db(session_obj)
        return question, expression

    def check_answer(self, answer):
        print("The answer is: " + str(answer))
        if (str(answer)).lower() == str(self.session['expected']):
            greeting = "Sehr gut. Dann habe ich andere Frage: "
            question, expression = self.get_question()
            expression['success'] = True
            question = greeting + " " + question
            return question, expression

        question = "Das stimmt leider nicht so ganz. Lass uns mal wieder probieren " + self.session['question']

        self.session['attempts'] += 1
        store_to_db(self.session)
        return question, self.session['expression']


class NumberGame(Game):

    def __init__(self, session):
        self.type = ALGEBRA
        super(NumberGame, self).__init__(session)

    def get_expression(self, num1, num2, operator):
        return {
            'num1': str(num1),
            'num2': str(num2),
            'operator': operator,
            'type': 'algebra',
            'success': False
        }

    def _curate_question(self):
        opeartions = ["add", "subtract", "multiply"]

        selected_operation = opeartions[randint(0, len(opeartions) - 1)]
        n1 = randint(1, 10)
        n2 = randint(1, 10)

        number_1 = min(n1, n2)
        number_2 = max(n1, n2)

        if selected_operation == "add":
            question = "Was ist die Summe von {0} und {1}"
            expected = number_1 + number_2
            expression = self.get_expression(number_1, number_2, '+')
        if selected_operation == "subtract":
            question = "Wie viel macht es wenn man {1} von {0} subtrahiert?"
            n1 = max(number_1, number_2)
            n2 = min(number_1, number_2)
            number_1 = n1
            number_2 = n2
            expected = number_1 - number_2
            expression = self.get_expression(number_1, number_2, '-')
        if selected_operation == "multiply":
            question = "{0} mal {1} mach wie viel...?"
            expected = number_1 * number_2
            expression = self.get_expression(number_1, number_2, '*')

        question = question.format(number_1, number_2)
        return question, str(expected), expression


class ShapeGame(Game):

    def __init__(self, session):
        self.type = SHAPE
        super(ShapeGame, self).__init__(session)

    def get_expression(self, shape):
        return {
            'shape': shape,
            'type': 'shape',
            'success': False
        }

    def _curate_question(self):
        shapes = ["quadrat", "dreieck", "kreis", "rechteck"]
        expected = shapes[randint(0, 1000000000) % 4]
        question = "Was ist diese Figur?"
        return question, expected, self.get_expression(expected)
