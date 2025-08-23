import { APIGatewayProxyHandler } from 'aws-lambda';
import { Client } from 'pg';

export const handler: APIGatewayProxyHandler = async (event) => {
  const client = new Client();
  await client.connect();

  const body = JSON.parse(event.body || '{}');
  const { id, name } = body;

  await client.query('INSERT INTO users (id, name) VALUES ($1, $2)', [id, name]);
  await client.end();

  return {
    statusCode: 200,
    body: JSON.stringify({ message: 'User inserted into PostgreSQL' }),
  };
};
