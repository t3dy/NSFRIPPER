import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import path from 'path';

export async function getDb() {
  return open({
    // Need an absolute or precise relative path to the database
    // The DB is at ANTIRIPPER/antiripper.db, and we are in ANTIRIPPER/web_portal
    filename: path.resolve(process.cwd(), '../antiripper.db'),
    driver: sqlite3.Database
  });
}
