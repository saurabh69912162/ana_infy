from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
from classifier import classify_input, access_and_authentication, networking_connectivity, hardware_device_issues, software_applications, collaboration_productivity_tools, security_compliance
from dotenv import load_dotenv
from database import init_db, insert_request, get_all_requests, get_db_connection, insert_comment,get_ticket_details
from datetime import datetime, timezone
import random,json
from mandatory_fields_and_user_mapping import MAPPING_DATA as mapping_data

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Initialize the database
init_db()



available_status = ['Open', 'Closed', 'In Progress', 'Pending', 'Resolved', 'Escalated']
available_categories = ['Access & Authentication', 'Networking & Connectivity', 'Hardware / Device Issues', 'Software / Applications', 'Collaboration & Productivity Tools', 'Security & Compliance']

@app.route('/', methods=['GET', 'POST'])
def index():
    name = email = development_center = query_text = None
    classification = None
    recent_tickets = []
    total_tickets = open_tickets = resolved_tickets = critical_tickets = 0
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        development_center = request.form.get('development_center')
        query_text = request.form.get('query_text')
        classification = classify_input(query_text)
        resolution = "NONE~NONE"
        # Insert request details into the database
        severity = classification.get('severity')
        urgency = classification.get('urgency')
        agent = classification.get('agent').replace(' ', '_') + '- AI Agent'
        
        if severity == 'High' or severity in ['Today', 'Immediate']:
            agent = 'To Be Assigned (IT TEAM)'
        
        if classification['category'] not in available_categories:
            classification['category'] = 'Others'
            agent = 'To Be Assigned (IT TEAM)'

        # open status by default
        request_id = insert_request(name, email, development_center, query_text, "Open", "Topic", "Main Issue", classification.get('category'),agent,severity,urgency,resolution)
        return redirect(url_for('ticket_details', id=request_id))
    else:
        # Fetch the last 5 recently created tickets
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, query_text, status FROM requests ORDER BY created_at DESC LIMIT 3')
        recent_tickets = cursor.fetchall()

        # Fetch total tickets
        cursor.execute('SELECT COUNT(*) FROM requests')
        total_tickets = cursor.fetchone()[0]

        # Fetch open tickets
        cursor.execute('SELECT COUNT(*) FROM requests WHERE status = "Open"')
        open_tickets = cursor.fetchone()[0]

        # Fetch resolved tickets
        cursor.execute('SELECT COUNT(*) FROM requests WHERE status = "Resolved"')
        resolved_tickets = cursor.fetchone()[0]

        # Fetch critical/high severity tickets
        cursor.execute('SELECT COUNT(*) FROM requests WHERE severity IN ("Critical", "High")')
        critical_tickets = cursor.fetchone()[0]

        conn.close()
    return render_template('index.html', name=name, email=email, development_center=development_center, query_text=query_text, classification=classification, recent_tickets=recent_tickets, total_tickets=total_tickets, open_tickets=open_tickets, resolved_tickets=resolved_tickets, critical_tickets=critical_tickets)

@app.route('/add_comment', methods=['POST'])
def add_comment():
    data = request.get_json()
    request_id = data.get('request_id')
    comment = data.get('comment')
    if not request_id or not comment:
        return jsonify({'success': False, 'message': 'Request ID and comment are required.'}), 400
    insert_comment(request_id, comment)
    return jsonify({'success': True, 'message': 'Comment added successfully.'})


@app.route('/ticket_details', methods=['GET', 'POST'])
def ticket_details():
    ticket_id = request.args.get('id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM requests WHERE id = ?', (ticket_id,))
    ticket = cursor.fetchone()
    cursor.execute('SELECT * FROM comments WHERE request_id = ? order by created_at desc', (ticket_id,))
    comments = cursor.fetchall()
    conn.close()
    # print('ticket category',ticket.category)
    if ticket is None:
        return "Ticket not found", 404
    
    category = ticket['category']
    extras = json.loads(ticket['extra_fields']) if ticket['extra_fields'] else {}
    missing_fields = []
    
    # Check for missing mandatory fields
    if not extras and category in mapping_data:
        mandatory_fields = mapping_data[category]['mandatory_fields']
        for field in mandatory_fields:
            if not extras.get(field):
                missing_fields.append(field)
    
    if request.method == 'POST':
        # Update ticket with filled mandatory fields
        extra_fields = {}
        for field in missing_fields:
            extra_fields.update({field: request.form.get(field)})
        ticket_category = ticket['category']
        ticket_query_text = ticket['query_text']
        classification_dict = {
            'category': ticket_category,
            'severity': ticket['severity'],
            'urgency': ticket['urgency'],
            'agent': ticket['agent_name']
        }
        # Call the resolution function if all fields are filled
        if extra_fields:
            resolution = None
            if ticket_category == 'Access & Authentication':
                resolution = access_and_authentication(classification_dict, ticket_query_text)
            elif ticket_category == 'Networking & Connectivity':
                resolution = networking_connectivity(classification_dict, ticket_query_text)
            elif ticket_category == 'Hardware / Device Issues':
                resolution = hardware_device_issues(classification_dict, ticket_query_text)
            elif ticket_category == 'Software / Applications':
                resolution = software_applications(classification_dict, ticket_query_text)
            elif ticket_category == 'Collaboration & Productivity Tools':
                resolution = collaboration_productivity_tools(classification_dict, ticket_query_text)
            elif ticket_category == 'Security & Compliance':
                resolution = security_compliance(classification_dict, ticket_query_text)
            else:
                resolution = "Resolution for other categories is not implemented yet."
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE requests SET resolution = ?, extra_fields = ? WHERE id = ?', (resolution, json.dumps(extra_fields), ticket_id))
            conn.commit()
            conn.close()
            return redirect(url_for('ticket_details', id=ticket_id))
    
    return render_template('ticket_details.html', ticket=ticket, comments=comments, missing_fields=missing_fields)

@app.route('/all_requests')
def all_requests():
    requests = get_all_requests()
    return render_template('all_requests.html', requests=requests)

@app.route('/resolve_ticket', methods=['POST'])
def resolve_ticket():
    data = request.get_json()
    if not data or 'ticket_id' not in data:
        return jsonify({'success': False, 'error': 'Invalid request data'}), 400
    ticket_id = data['ticket_id']
    ticket = get_ticket_details(ticket_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    # Update the ticket status and closing time
    closing_time = datetime.now()
    cursor.execute('''
        UPDATE requests
        SET status = ?, closing_time = ?
        WHERE id = ?
    ''', ('Resolved', closing_time, ticket_id))
    
    # Calculate the time taken to close the ticket
    cursor.execute('SELECT created_at FROM requests WHERE id = ?', (ticket_id,))
    created_at = cursor.fetchone()['created_at']
    conn.commit()
    
    time_taken = int((closing_time - datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')).total_seconds())
    cursor.execute('''
        UPDATE requests
        SET time_taken = ?
        WHERE id = ?
    ''', (time_taken, ticket_id))

    # Add resolution comment
    cursor.execute('''
    INSERT INTO comments (request_id, comment)
    VALUES (?, ?)
    ''', (ticket_id, 'This ticket has been resolved [BY USER]'))

    # Insert into knowledgebase
    if ticket['resolution'] and ticket['resolution'].lower() != 'none~none':
        cursor.execute('''
                INSERT INTO knowledgebase (category, issue_description, resolution)
                VALUES (?, ?, ?)
                ''', (ticket['category'], ticket['query_text'], ticket['resolution']))

    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/knowledge_base')
def knowledge_base():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch all data from the knowledgebase table
    cursor.execute('SELECT * FROM knowledgebase ORDER BY category')
    knowledgebase_entries = cursor.fetchall()
    conn.close()
    return render_template('knowledge_base.html', knowledgebase_entries=knowledgebase_entries)

@app.route('/analytics')
def analytics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query for tasks handled by AI agents and IT team
    cursor.execute('''
        SELECT 
            CASE 
                WHEN agent_name LIKE '%AI Agent%' THEN 'AI Agent'
                WHEN agent_name = 'To Be Assigned (IT TEAM)' THEN 'Not Assigned'
                WHEN agent_name LIKE '%@%' THEN 'IT TEAM'
                ELSE 'IT TEAM'  -- catch-all
            END AS assigned_team,
            COUNT(*) AS task_count
        FROM requests
        GROUP BY assigned_team;
    ''')
    agent_task_distribution = cursor.fetchall()
    
    # Transform the data into a list of dictionaries
    agent_task_distribution = [
        {'agent_name': row[0], 'task_count': row[1]}
        for row in agent_task_distribution
    ]
    
    # Query for AI agent vs IT team task distribution
    cursor.execute('''
        SELECT 
            CASE 
                WHEN agent_name LIKE '%AI Agent%' THEN 'AI Agents'
                WHEN agent_name = 'To Be Assigned (IT TEAM)' THEN 'Not Assigned'
                WHEN agent_name LIKE '%@%' THEN 'IT Team'
                ELSE 'IT Team' -- catch-all
            END AS agent_type,
            COUNT(*) AS task_count
        FROM requests
        GROUP BY agent_type;
    ''')
    ai_vs_it_distribution = cursor.fetchall()
    
    # Transform the data into a list of dictionaries
    ai_vs_it_distribution = [
        {'agent_type': row[0], 'task_count': row[1]}
        for row in ai_vs_it_distribution
    ]
    
    # Query for average time taken by AI agents vs IT team
    cursor.execute('''
        SELECT 
            CASE 
                WHEN agent_name LIKE '%AI Agent%' THEN 'AI Agents'
                WHEN agent_name = 'To Be Assigned (IT TEAM)' THEN 'Not Assigned'
                ELSE 'IT Team'
            END AS agent_type, 
            AVG(time_taken) AS avg_time,
            COUNT(*) AS ticket_count
        FROM requests
        WHERE time_taken IS NOT NULL 
        AND time_taken > 0
        GROUP BY agent_type;
    ''')
    avg_time_distribution = cursor.fetchall()
    # Transform the data into a list of dictionaries and convert seconds to readable format
    avg_time_distribution_data = []
    for row in avg_time_distribution:
        seconds = row[1]
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        time_str = ""
        if hours > 0:
            time_str += f"{hours}h "
        if minutes > 0:
            time_str += f"{minutes}m "
        time_str += f"{seconds}s"
        
        avg_time_distribution_data.append({
            'agent_type': row[0],
            'avg_time': time_str.strip(),
            'ticket_count': row[2]
        })

    # Query for feedback distribution
    cursor.execute('''
        SELECT points, COUNT(*) as count
        FROM feedback
        GROUP BY points
    ''')
    feedback_distribution = cursor.fetchall()
    feedback_distribution = [
        {'points': row[0], 'count': row[1]}
        for row in feedback_distribution
    ]
    print('feedback_distribution',feedback_distribution)
    
    conn.close()
    return render_template('analytics.html', agent_task_distribution=agent_task_distribution, ai_vs_it_distribution=ai_vs_it_distribution, avg_time_distribution=avg_time_distribution_data, feedback_distribution=feedback_distribution)

@app.route('/insert_random_records', methods=['GET'])
def insert_random_records():
    categories = [
        'Access & Authentication',
        'Networking & Connectivity',
        'Hardware / Device Issues',
        'Software / Applications',
        'Collaboration & Productivity Tools',
        'Security & Compliance'
    ]
    agents = [
        'AI Agent 1',
        'AI Agent 2',
        'AI Agent 3',
        'AI Agent 4',
        'AI Agent 5',
        'AI Agent 6'
    ]
    
    for _ in range(50):
        name = f'User{random.randint(1, 1000)}'
        email = f'user{random.randint(1, 1000)}@example.com'
        development_center = f'DC{random.randint(1, 10)}'
        query_text = f'Query {random.randint(1, 1000)}'
        status = random.choice(['Open', 'Resolved'])
        topic = f'Topic {random.randint(1, 10)}'
        main_issue = f'Main Issue {random.randint(1, 3)}'
        category = random.choice(categories)
        agent_name = random.choice(agents)
        severity = random.choice(['Low', 'Medium', 'High'])
        urgency = random.choice(['Today','Low', 'Medium', 'High', 'Immediate'])
        resolution = f'Resolution {random.randint(1, 100)}'
        
        insert_request(name, email, development_center, query_text, status, topic, main_issue, category, agent_name, severity, urgency, resolution)
    
    return '200 random records inserted successfully.'

@app.route('/search_ticket', methods=['POST'])
def search_ticket():
    data = request.get_json()
    if not data or 'ticket_id' not in data:
        return jsonify({'success': False, 'error': 'Invalid request data'}), 400
    ticket_id = data['ticket_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM requests WHERE id = ?', (ticket_id,))
    ticket = cursor.fetchone()
    conn.close()
    if ticket:
        return jsonify({'success': True, 'redirect_url': url_for('ticket_details', id=ticket_id)})
    else:
        return jsonify({'success': False, 'error': 'Ticket ID not found'})



@app.route('/escalate_pending_tasks', methods=['POST'])
def escalate_pending_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all unresolved AI agent tickets from yesterday
    cursor.execute('''
    SELECT id FROM requests 
    WHERE agent_name LIKE '%AI Agent%' 
    AND status != 'Resolved'
    ''')
    escalated_tickets = cursor.fetchall()
    
    # Add escalation comment and update status for each ticket
    for ticket in escalated_tickets:
        # Add escalation comment
        cursor.execute('''
        INSERT INTO comments (request_id, comment)
        VALUES (?, ?)
        ''', (ticket[0], 'This ticket has been escalated & assigned to IT team [BY SYSTEM]'))

        # Update ticket status to Escalated
        cursor.execute('''
        UPDATE requests
        SET status = 'Escalated'
        WHERE id = ?
        ''', (ticket[0],))
        
        # Update ticket agent name to IT team
        cursor.execute('''
        UPDATE requests
        SET agent_name = 'To Be Assigned (IT TEAM)'
        WHERE id = ?
        ''', (ticket[0],))
        
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'All pending tasks from yesterday assigned to AI agents have been escalated.'})

@app.route('/auto_assign_tasks', methods=['POST'])
def auto_assign_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch all tasks assigned to IT team
    cursor.execute('SELECT id, category FROM requests WHERE agent_name = "To Be Assigned (IT TEAM)" and status != "Resolved"')
    tasks = cursor.fetchall()
    for task in tasks:
        category = task['category']
        if category in mapping_data:
            # Get a random user from dummy_users for the category
            user = random.choice(mapping_data[category]['dummy_users'])
            # Update the task with the assigned user
            cursor.execute('''
            UPDATE requests
            SET agent_name = ?, email = ?
            WHERE id = ?
            ''', (user['user_name'], user['email'] + "[IT-TEAM]", task['id']))

            # Add assignment comment
            cursor.execute('''
            INSERT INTO comments (request_id, comment)
            VALUES (?, ?)
            ''', (task[0], 'This ticket has been assigned to ' + user['user_name'] + " [BY SYSTEM]"))

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Tasks have been auto-assigned to IT team members.'})

@app.route('/escalate_issue', methods=['POST'])
def escalate_issue():
    data = request.get_json()
    ticket_id = data.get('ticket_id')
    if not ticket_id:
        return jsonify({'success': False, 'message': 'Ticket ID is required.'}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    # Update the status of the specific ticket to 'Escalated'
    cursor.execute('''
    UPDATE requests
    SET status = 'Escalated'
    WHERE id = ?
    ''', (ticket_id,))

    cursor.execute('''
    INSERT INTO comments (request_id, comment)
    VALUES (?, ?)
    ''', (ticket_id, 'This ticket has been escalated [ESCALATED BY USER]'))

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f'Ticket {ticket_id} has been escalated.'})

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    data = request.get_json()
    ticket_id = data.get('ticket_id')
    points = data.get('points')
    feedback_text = data.get('feedback_text')
    if not ticket_id or points is None:
        return jsonify({'success': False, 'message': 'Ticket ID and points are required.'}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO feedback (ticket_id, points, feedback_text)
    VALUES (?, ?, ?)
    ''', (ticket_id, points, feedback_text))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Feedback submitted successfully.'})

@app.route('/readme')
def readme():
    return render_template('readme.html')

@app.route('/tech-stack')
def tech_stack():
    return render_template('techstack.html')

@app.route('/architechure-diagram')
def architechure_diagram():
    return render_template('architechure-diagram.html')

@app.route('/user-personas')
def user_personas():
    return render_template('user_person.html')

if __name__ == '__main__':
    app.run(debug=True) 