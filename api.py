from random import randint
from flask import Blueprint
from helper import *
import time

api = Blueprint('api', __name__, template_folder='templates')


def error():
    response = jsonify({'message': "THIS SI ERROR"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.status_code = 400
    return response


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


@api.route('/around-movie/')
@api.route('/around-movie/<title>')
@crossdomain(origin='*')
def around_movie(title=""):
    node = found_movie(title)
    if node is None:
        return error_response()

    g = graph.cypher.execute("MATCH p=(m)<-[]-(a) WHERE m.title = {title} AND (a:Actor OR a:Director)"
                             " return p", title=title)
    data = graph_to_nodes_edges(g)
    data['movie'] = node
    return jsonify(data)



@api.route('/around-person/')
@api.route('/around-person/<name>')
@crossdomain(origin='*')
def around_person(name=""):
    node = found_person(name)
    if node is None:
        return error_response()
    g = graph.cypher.execute("MATCH p=(a)-[r]-(:Movie) WHERE a.name = {name} AND (a:Actor OR a:Director)"
                             " RETURN p", name=node['name'])
    data = graph_to_nodes_edges(g)
    data['person'] = node
    return jsonify(data)


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


def error_response():
    response = jsonify({'message': "THIS SI ERROR"})
    response.status_code = 400
    return response



