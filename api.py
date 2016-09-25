from random import randint

from flask import Blueprint, jsonify
from flask import render_template

from helper import *

api = Blueprint('api', __name__, template_folder='templates')


@api.route('/')
def test22():
    return "HEHEHEH2"


@api.route('/error')
def error():
   # message = jsonify({"message": "this error is very good"})
    response = jsonify({'message': "THIS SI ERROR"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.status_code = 400
    return response

@api.route('/test')
def test():
    return render_template("test.html")


@api.route("/search/person/")
@api.route("/search/person/<pattern>")
@crossdomain(origin='*')
def search_person(pattern=""):
    regex = '(?i).*{}.*'.format(pattern)
    g = graph.cypher.execute("MATCH (a) WHERE a.name =~ '{}' AND (a:Actor OR a:Director) "
                             "RETURN a.name LIMIT {}".format(regex, 10))
    actors = [x[0] for x in g]
    return jsonify({"results": actors})


@api.route("/search/movie/")
@api.route("/search/movie/<pattern>")
@crossdomain(origin='*')
def search_movie(pattern=""):
    regex = '(?i).*{}.*'.format(pattern)
    g = graph.cypher.execute("MATCH (m:Movie) WHERE m.title =~ {title}"
                             " RETURN m.title LIMIT {limit}", title=regex, limit=10)
    movies = [x[0] for x in g]
    return jsonify({"results": movies})

@api.route("/search/director/<pattern>")
def search_director(pattern):
    return search_actor_or_director(pattern, 'Director')


@api.route("/two-actors-movies/<a>/<b>")
def get_two_actor_collaborations(a, b):
    if not actor_exist(a):
        return jsonify({"status": "error", "message": "Actor called {0} does not exit".format(a)})
    if not actor_exist(b):
        return jsonify({"status": "error", "message": "Actor called {0} does not exit".format(b)})

    g = graph.cypher.execute("Match p=(a:Actor)-[:ACTS_IN]->(b:Movie) where a.name in [{a1}, {a2}] "
                             "return p", a1=a, a2=b)

    return jsonify(graph_to_nodes_edges(g))


@api.route("/actor-director-collab/<a>/<d>")
def get_actor_director_collab(a, d):
    if not director_exists(d):
        return jsonify({"status": "error", "message": "Director called {0} does not exit".format(d)})
    if not actor_exist(a):
        return jsonify({"status": "error", "message": "Actor called {0} does not exit".format(a)})

    g = graph.cypher.execute("MATCH p=(a:Actor{name:{ac}})-[:ACTS_IN]->(m)<-[:DIRECTED]-(d:Director{name:{dr}})"
                             " RETURN p", ac=a, dr=d)

    return jsonify(graph_to_nodes_edges(g))


@api.route("/actor-collab-top/<actor>")
def get_actor_to_other_actors_collaborations_top(actor, limit=10):
    g = graph.cypher.execute("MATCH (a:Actor{name:{name}})-[:ACTS_IN]->(m:Movie)<-[:ACTS_IN]-(b:Actor)"
                             " RETURN a.name, b.name, count(m) AS c ORDER BY c DESC LIMIT {limit}", name=actor, limit=limit)
    return jsonify([[x[0], x[1], x[2]] for x in g.records])


@api.route("/around-node/<node_id>/<group>")
@crossdomain(origin='*')
def get_nodes_around(node_id, group):
    if group not in ['Movie', 'Actor', 'Director']:
        return "BAD"
    if group == 'Movie':
        g = graph.cypher.execute("MATCH p=(:Movie{title:{id}})-[]-(n) WHERE n:Actor OR n:Director "
                                 "RETURN p", id=node_id)
    elif group == 'Actor':
        g = graph.cypher.execute("MATCH p=(:Actor{name:{id}})-[r]-(:Movie) RETURN p", id=node_id)
    else:
        g = graph.cypher.execute("MATCH p=(:Director{name:{id}})-[r]-(:Movie) RETURN p", id=node_id)
    return jsonify(graph_to_nodes_edges(g))


@api.route('/random-graph')
@crossdomain(origin='*')
def random_graph():
    skip = randint(0, 100)
    g = graph.cypher.execute("MATCH p = ()-[]-()-[]-() return p skip {skip} limit 5", skip=skip)
    return jsonify(graph_to_nodes_edges(g))


@api.route("/stats")
@crossdomain(origin='*')
def main_page_stats():
    movie_count = get_movie_count()
    actor_count = get_actor_count()
    role_count = get_role_count()
    director_count = get_director_count()

    stats = {
        "movie_count": movie_count,
        "actor_count": actor_count,
        "role_count": role_count,
        "director_count": director_count
    }

    return jsonify(stats)


def error_response():
    response = jsonify({'message': "THIS SI ERROR"})
    response.status_code = 400
    return response


def get_node_label(node):
    if 'Movie' in node.labels:
        return 'Movie'
    elif 'Director' in node.labels and 'Actor' not in node.labels:
        return 'Director'
    return 'Actor'

@api.route('/around-movie/')
@api.route('/around-movie/<title>')
@crossdomain(origin='*')
def around_movie(title=""):
    node = found_movie(title)
    if node is None:
        return error_response()

    g = graph.cypher.execute("MATCH p=(m)<-[]-(a) WHERE m.title = {title} AND (a:Actor OR a:Director) return p", title=title)
    data = graph_to_nodes_edges(g)
    data['movie'] = node
    return jsonify(data)


def found_movie(title):
    g = graph.cypher.execute("MATCH (m) where m.title = {title} RETURN m LIMIT 1", title=title)
    nodes = g.to_subgraph().nodes
    if len(nodes) == 0:
        return None
    for n in nodes:
        node = n
    movie = {
        'id': node['title'],
        'title': node['title'],
        'releaseDate': node['releaseDate'],
        'description': node['description'],
        'moviedb_id': node['id'],
        'genre': node['genre'],
        'runtime': node['runtime']
    }
    return movie


@api.route('/around-person/')
@api.route('/around-person/<name>')
@crossdomain(origin='*')
def around_person(name=""):
    node = found_person(name)
    if node is None:
        return error_response()
    g = graph.cypher.execute("MATCH p=(a)-[r]-(:Movie) WHERE a.name = {name} AND (a:Actor OR a:Director) RETURN p", name=node['name'])
    data = graph_to_nodes_edges(g)
    data['person'] = node
    return jsonify(data)

import time
@api.route('/collaboratiosn/<first>/')
@api.route('/collaborations/<first>/<second>')
@crossdomain(origin='*')
def collaborations(first="", second=""):
    start = time.time()
    person1 = found_person(first)
    if person1 is None:
        return error_response()
    person2 = found_person(second)
    if person2 is None:
        return error_response()

    g = graph.cypher.execute("MATCH p=(a:Person)-[]->(:Movie)<-[]-(b:Person)"
                             " WHERE a.name = {p1} AND b.name = {p2} "
                             " RETURN p", p1=person1['name'], p2=person2['name'])

    data = graph_to_nodes_edges(g)
    data['person1'] = person1
    data['person2'] = person2
    print(time.time()-start)

    return jsonify(data)


def found_person(name):
    g = graph.cypher.execute("MATCH (a:Person) WHERE a.name = {name} RETURN a LIMIT 1", name=name)
    nodes = g.to_subgraph().nodes
    if len(nodes) == 0:
        return None

    for n in nodes:
        node = n

    if only_person(node):
        return None

    person = {
        "id": node['name'],
        "name": node['name'],
        "moviedb_id": node['id'],
        "birthplace": node['birthplace'],
        "biography": node['biography'],
        "birthday": node['birthday'],
        "group": get_node_label(node)
    }

    return person


def only_person(node):
    return 'Person' in node.labels and len(node.labels) == 1

@api.route("/random-actor")
def random_actor():
    actor_count = get_actor_count()
    skip = randint(1, actor_count) - 1
    g = graph.cypher.execute_one("MATCH (a:Actor) RETURN a SKIP {skip} LIMIT 1", skip=skip)
    print(g)
    return jsonify(graph_to_nodes_edges(g))

