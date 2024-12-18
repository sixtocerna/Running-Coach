from pydantic_ai import Agent, ModelRetry
import logfire
from typing import List, Optional
from models import IntensityType, Target, Interval, WorkoutComponent
from pydantic_core import ValidationError


ExtractWorkoutComponentsAgent = Agent(
    'openai:gpt-4o-mini',
    system_prompt=(
        """
        You are an AI that converts workout plans into structured objects. Based on the workout description provided, generate the output as Python objects.

        Input Example:
        Warm-Up
            Description: Gradually increase your heart rate and prepare your muscles for the workout.
            Parameters: Time: 10 minutes, Pace: 6:00 min/km, Effort: 60%
        Intervals
            Repetitions: 5
            Subsets:
                Hard Interval: Short, intense segment at race pace. Time: 2 minutes, Pace: 4:15 min/km, Effort: 95%
                Recovery Interval: Easy jogging to recover. Time: 2 minutes, Pace: 6:00 min/km, Effort: 60%
        Cool Down
            Description: Gradually lower your heart rate and help your body recover.
            Parameters: Time: 10 minutes, Pace: 6:30 min/km, Effort: 50%

        Expected Output:
        [
            WorkoutComponent(name="1 Warm-Up", description="Gradually increase your heart rate and prepare your muscles for the workout.", parameters="Time: 10 minutes, Pace: 6:00 min/km, Effort: 60%", repetitions=None, subsets=[]),
            WorkoutComponent(name="2 Intervals", description="", parameters="", repetitions=5, subsets=["2.1 Hard Interval: Short, intense segment at race pace. Time: 2 minutes, Pace: 4:15 min/km, Effort: 95%", "2.2 Recovery Interval: Easy jogging to recover. Time: 2 minutes, Pace: 6:00 min/km, Effort: 60%"]),
            WorkoutComponent(name="3 Cool Down", description="Gradually lower your heart rate and help your body recover.", parameters="Time: 10 minutes, Pace: 6:30 min/km, Effort: 50%", repetitions=None, subsets=[])
        ]
        """
    ),
    result_type=List[WorkoutComponent]
)

ExtractIntervalsAgent = Agent(
    'openai:gpt-4o-mini',
    system_prompt="""
    You are an AI assistant tasked with creating structured workout intervals using the to_interval_obj function. Given a list of WorkoutComponent objects, 
    your goal is to analyze each component and its subsets to produce a nested Interval object. Follow these steps for each component:
    Identify Component Type:
        If the component has repetitions, it represents a repeated set and should use the repeat exit_trigger_type. Don't set targets in that case
        If no repetitions are present, the interval is singular and should use time or distance based on the parameters
    Extract Parameters:
        Parse the parameters string to determine duration (Time) or distance, effort level, and pace.
        Convert duration to seconds, pace to meters/second
    Create Nested Intervals:
        For components with subsets, treat each subset as a separate interval and nest them using the intervals parameter.
        For subsets, use their respective parameters and descriptions to determine targets.
    Define Targets:
        Set targets based on parsed speed. Make sure to use the pace parameter to determine the min and the max pace
    Set Intensity Type:
        Intensity is one of 'active', 'warm up', 'tempo', 'lactate threshold', 'maximal aerobic power', 'anaerobic capacity', 'cool down', 'recovery' or 'rest'

    Example Transformation:
    Given the WorkoutComponent list:

    [
    WorkoutComponent(
        name="1 Warm-Up",
        description="Gradually increase your heart rate and prepare your muscles for the workout.",
        parameters="Time: 10 minutes, Pace: 6:00 min/km, Effort: 60%",
        repetitions=None,
        subsets=[]
    ),
    WorkoutComponent(
        name="2 Intervals",
        description="",
        parameters="",
        repetitions=5,
        subsets=[
            "2.1 Hard Interval: Short, intense segment at race pace. Time: 2 minutes, Pace: 4:15 min/km, Effort: 95%",
            "2.2 Recovery Interval: Easy jogging to recover. Time: 2 minutes, Pace: 6:00 min/km, Effort: 60%"
        ]
    ),
    WorkoutComponent(
        name="3 Cool Down",
        description="Gradually lower your heart rate and help your body recover.",
        parameters="Time: 10 minutes, Pace: 6:30 min/km, Effort: 50%",
        repetitions=None,
        subsets=[]
    )
]

    Expected Output:

    [
    Interval(
        name="1 Warm-Up",
        exit_trigger_type="time",
        exit_trigger_value=600,  # 10 minutes in seconds
        intensity_type="60%",
        targets=[
            Target(
                type="speed",
                low=2.78,  # 6:00 min/km converted to m/s
                high=2.78
            )
        ],
        intervals=None
    ),
    Interval(
        name="2 Intervals",
        exit_trigger_type="repeat",
        exit_trigger_value=5,
        intensity_type=None,
        targets=None,
        intervals=[
            Interval(
                name="2.1 Hard Interval",
                exit_trigger_type="time",
                exit_trigger_value=120,  # 2 minutes in seconds
                intensity_type="95%",
                targets=[
                    Target(
                        type="speed",
                        low=3.92,  # 4:15 min/km converted to m/s
                        high=3.92
                    )
                ],
                intervals=None
            ),
            Interval(
                name="2.2 Recovery Interval",
                exit_trigger_type="time",
                exit_trigger_value=120,  # 2 minutes in seconds
                intensity_type="60%",
                targets=[
                    Target(
                        type="speed",
                        low=2.78,  # 6:00 min/km converted to m/s
                        high=2.78
                    )
                ],
                intervals=None
            )
        ])
    ]
    """, 
    result_type=list[Interval]
)

@ExtractIntervalsAgent.tool_plain(retries=5)
def to_inverval_obj(name:Optional[str], exit_trigger_type:str, exit_trigger_value:int, targets:Optional[List[Target]]|None, intervals:List[Interval]|None, intensity_type:IntensityType=None)->Interval:
    """"
    Returns an Interval object

    name : Display name for the interval 
    exit_trigger_type : can be one of time, distance or repeat (use repeat if you want to repeat several times this interval)
    exit_trigger_value : Value for the exit trigger (duration in seconds, distance in meters, or repetitions)
    intensity_type : one of 'active', 'warm up', 'tempo', 'lactate threshold', 'maximal aerobic power', 'anaerobic capacity', 'cool down', 'recovery' or 'rest'
    targets : List of target values and controls for the interval, valid only if exit_trigger_type is not 'repeat'
    intervals : Nested intervals used for repetitions when exit_trigger_type is 'repeat'

    Target is a dictionnary with the following keys:
    type(str): 'speed' for speed target in meters per second or 'threshold_speed' for percentage of athlete’s threshold speed
    low(float): The lowest value for the target to be considered 'in range'
    high(float): The highest value for the target to be considered 'in range'
    """

    try:
        output = Interval(name=name, exit_trigger_type=exit_trigger_type, exit_trigger_value=exit_trigger_value, intensity_type=intensity_type, targets=targets, intervals=intervals)
    except ValidationError as e:
        logfire.debug(msg='Failed at creating interval with because {e}', e=str(e), attributes=dict(name=name, exit_trigger_type=exit_trigger_type, exit_trigger_value=exit_trigger_value, intensity_type=intensity_type, targets=targets, intervals=intervals))
        raise ModelRetry(message=str(e))
    
    return output


@ExtractIntervalsAgent.tool_plain
def from_minutes_to_secs(minutes:int, seconds:int):
    # Transforms the input from minutes to seconds
    return minutes*60 + seconds

@ExtractIntervalsAgent.tool_plain(retries=1)
def from_pace_to_speed_mps(pace_min:int, pace_sec:int):
    # Transforms a pace to meters per second
    total_seconds_per_km = (pace_min * 60) + pace_sec
    return round(1000 / total_seconds_per_km, 3)


WorkoutGenerationAgent = Agent(  
    'openai:gpt-4o-mini',
    system_prompt=(
        'You are a running coach. You have to provide the user '
        'with a running workout session for today. Take into account his current level '
        '(use his previous workouts as a guideline), his running goals, the feedback '
        'he has given you during previous workouts and other factors such as how long it has '
        'been since the last workout, what kind of workout it was, how difficult was it and '
        'how much time it has available today. Do not include streching in the workout, only'
        'a warm up and and a cool down.'
        'Make sure to include a different types of workouts : '
        '- Steady Runs: Moderate effort to build aerobic capacity. '
        '- Intervals: Short bursts at race pace or faster for speed development. '
        '- Tempo Runs: Sustainable high-effort pace to improve lactate threshold. '
        '- Hill Repeats: Develops strength and running form. '
        '- Recovery Runs: Easy pace to support regeneration. '
        '- Long Runs: Gradually increased distance to build endurance. ' 
        'Do not provide anything related to streching. '
        'Present the information for each interval as follows : '
    ) + """
        If there are not subsets : 
        ## x Name 
        - Description : ..., 
        - Parameters : Time: ..., Pace: ..., 
        If there are subsets : 
        ### x Name
        - Repetitions: ... (how many times to repeat the subsets)
        - Subsets : 
            ## x.1 Name 
            - Description : ..., 
            - Parameters : Time: ..., Pace: ...
        Consider the warmup as the first interval. DO NOT TALK ABOUT EFFORT. PROVIDE THE PACE IN MIN/KM. ALWAYS PROVIDE AN INTERVAL OF PACES.
        Finally please use the tools to retrive information about the last workouts
        """,

)

SummarizerAgent = Agent(
    'openai:gpt-4o-mini',
    system_prompt='Please summarize in less than 50 words the following traning : description and how it will help me achieve my goals'
)