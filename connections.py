import requests
from auth import token_manager
from datetime import datetime, UTC, timedelta
from models import WorkoutData, WorkoutEndpointResponseJSONModel
import sqlite3
import json
import logging
from utils import setup_logger

logger = setup_logger('api_logs.log')

class WahooAPI:

    def __init__(self):
        self.token_manager = token_manager
        self.base_url = 'https://api.wahooligan.com/v1/'
        
    @property
    def headers(self):
        return {'Authorization':f'Bearer {self.token_manager.get_access_token()}'}


    def _get_workouts_page(self, page:int, per_page) -> WorkoutEndpointResponseJSONModel:

        url = self.base_url + 'workouts'

        response = requests.get(
            url = url,
            headers=self.headers,
            params={'page':page, 'per_page':per_page} # Per page high reduces the number of API calls required
        )

        response.raise_for_status()

        return WorkoutEndpointResponseJSONModel(**response.json())
    

    def read_workouts(self, after:datetime|None=None, per_page:int=50) -> list[WorkoutData]:
        # After date is in UTC. After is strict

        first_page = self._get_workouts_page(1, per_page=per_page)

        output = [w for w in first_page.workouts]

        total = first_page.total

        if after:
            # Get only workouts after the specified date

            # Prevent error of comparing naive tz (from after) with UTC time (from API)
            assert after.timetz().tzinfo == UTC, 'Before must be a datetime with UTC'

            last_date_in_response = first_page.lastest_starts_date_in_page

            next_page_num = 2

            # Only go to next page if there are more workouts that could be in the next page
            # that means there are still unseen workouts in later pages that could have
            # a date bafter the selected date

            while last_date_in_response >= after and len(output)<total:
                
                next_page = self._get_workouts_page(next_page_num, per_page=per_page)

                last_date_in_response = next_page.lastest_starts_date_in_page

                output.extend(next_page.workouts)

            return [w for w in output if w.starts>after]

        else:

            # Get all workouts

            next_page_num = 2

            while total > len(output):

                new_page = self._get_workouts_page(next_page_num, per_page=per_page)

                output.extend(new_page.workouts)

                next_page_num +=1

            return output
    

    def update_plan(self):
        ...

    def upload_plan(self):
        ...

    def delete_plan(self):
        ...

class DatabaseAPI:

    def __init__(self, db_file:str, logger:logging.Logger):
        self.db_file = db_file
        self.logger = logger

    def _create_workouts_table(self, cursor:sqlite3.Cursor):

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INT NOT NULL PRIMARY KEY,
            starts DATETIME NOT NULL,
            minutes INT NOT NULL,
            name VARCHAR(255) NOT NULL,
            plan_id INT NULL,
            route_id INT NULL,
            workout_token VARCHAR(255) NOT NULL,
            workout_type_id INT NOT NULL,
            day_code INT NULL,
            workout_summary JSON NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );
        ''')

    def _create_feedback_table(self, cursor:sqlite3.Cursor):

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INT NOT NULL,
            rpe INT NOT NULL,
            feedback TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE
        );
        ''')

    def _create_plan_table(self, cursor:sqlite3.Cursor):

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INT NOT NULL,
            content JSON NOT NULL,
            FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE
        );
        ''')

    def _create_all_tables(self):

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        self._create_workouts_table(cursor)
        self._create_feedback_table(cursor)
        self._create_plan_table(cursor)

        conn.commit()
        conn.close()

    def update_workouts_table(self):

        # Get most recent workout date
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        query = "SELECT MAX(starts) FROM workouts"
        response = cursor.execute(query)
        most_recent_workout_date = response.fetchone()[0]

        wahoo = WahooAPI()

        # If the table was empty get all workouts
        if most_recent_workout_date is None:
            workouts_to_upload_locally = wahoo.read_workouts()
        # If there was at least one workout
        else:
            # Add one minute to not bring the most recent from the API
            # and prevent a unique ID error on the database

            most_recent_workout_date = datetime.fromisoformat(most_recent_workout_date)

            workouts_to_upload_locally = wahoo.read_workouts(after=most_recent_workout_date)
        
        # Add them to the database

        self.logger.info(f'Uploading {len(workouts_to_upload_locally)} workouts to database : after {most_recent_workout_date}')

        for workout in workouts_to_upload_locally:
            try: 
                self.upload_workout(workout, cursor)
            except sqlite3.Error as e:
                self.logger.error(f'Failed to upload workout with id {workout.id} : {e}')
            else:
                self.logger.info(f'Succesfully uploaded workout')

        conn.commit()
        conn.close()

    def upload_workout(self, workout:WorkoutData, cursor:sqlite3.Cursor):
        
        insert_query = """
        INSERT INTO workouts (
            id, starts, minutes, name, plan_id, route_id, workout_token,
            workout_type_id, day_code, workout_summary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        cursor.execute(insert_query, (
            workout.id,
                workout.starts.strftime('%Y-%m-%dT%H:%M:%S.000+00:00'),  # Convert datetime to ISO 8601 string
                workout.minutes,
                workout.name,
                workout.plan_id,
                workout.route_id,
                workout.workout_token,
                workout.workout_type_id,
                workout.day_code,
                json.dumps(workout.workout_summary) if workout.workout_summary else None,  # Convert dict to string (JSON)
                workout.created_at.strftime('%Y-%m-%dT%H:%M:%S.000+00:00'),
                workout.updated_at.strftime('%Y-%m-%dT%H:%M:%S.000+00:00')
        )
        )
        
    def recent_workouts_data(self, num:int=5) -> list[WorkoutData]:

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        query = f'SELECT * FROM workouts ORDER BY starts DESC LIMIT {num}'

        result = cursor.execute(query).fetchall()

        conn.close()

        workouts = [
            WorkoutData(**{
                    'id': r[0],
                    'starts': r[1],
                    'minutes': r[2],
                    'name': r[3],
                    'plan_id': r[4],
                    'route_id': r[5],
                    'workout_token': r[6],
                    'workout_type_id': r[7],
                    'day_code': r[8],
                    'workout_summary': json.loads(r[9]),
                    'created_at': r[10],
                    'updated_at': r[11]}
                    ) 
            for r in result
            ]
        

        return workouts

    def add_feedback_most_recent_workout(self, rpe:int, msg:str):

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        query = "SELECT id FROM workouts WHERE starts = (SELECT MAX(starts) FROM workouts)"
        response = cursor.execute(query)
        most_recent_workout_id = response.fetchone()[0]

        self._add_feedback(most_recent_workout_id, rpe, msg)

        conn.commit()
        conn.close()  
    
    def _add_feedback(self, workout_id:int, rpe:int, msg:str):

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        insert_query = "INSERT INTO feedback (workout_id, rpe, feedback) VALUES (?, ?, ?)"

        cursor.execute(insert_query, (workout_id, rpe, msg))

        conn.commit()
        conn.close()

        self.logger.info(f'Added feedback to workout {workout_id}')
        

    def get_feedback_from_workouts(self, workouts_id:list[int])->list[dict[int, dict]]:
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        placeholders = ', '.join('?' for _ in workouts_id)
    
        query = f'SELECT workout_id, rpe, feedback FROM feedback WHERE workout_id IN ({placeholders})'
        query_results = cursor.execute(query, tuple(workouts_id))
        
        found = [{'workout_id':r[0], 'rpe':r[1], 'feedback':r[2]} for r in query_results]
        ids_with_feedback = [r['workout_id'] for r in found]
        not_found = [{'workout_id':id_, 'rpe':None, 'feedback':None} for id_ in workouts_id if id_ not in ids_with_feedback]

        conn.close()

        return found + not_found

    def add_plan(self, plan_data):
        ...

    