from pkg_resources._vendor.pyparsing import basestring

from common import graph
from flask import jsonify


def graph_to_nodes_edges(data):
    g = data.to_subgraph()
    nodes = []
    edges = []
    for node in g.nodes:
        if 'Movie' in node.labels:
            nodes.append({'id': node['title'], 'group': 'Movie'})
        elif 'Director' in node.labels and 'Actor' not in node.labels:
            nodes.append({'id': node['name'], 'group': 'Director'})
        elif 'Actor' in node.labels:
            nodes.append({'id': node['name'], 'group': 'Actor'})

    for edge in g.relationships:
        sn_id = get_node_id(edge.start_node)
        en_id = get_node_id(edge.end_node)
        edges.append({'source': sn_id, 'target': en_id, 'group': edge.type, 'role': edge['name']})

    return {'nodes': nodes,
            'links': edges}


def search_actor_or_director(pattern, label, limit=10):
    regex = '(?i).*{}.*'.format(pattern)
    g = graph.cypher.execute("MATCH (a:{}) WHERE a.name =~ {{regex}} "
                             "RETURN a.name LIMIT {{limit}}".format(label), regex=regex, limit=limit)
    actors = [x[0] for x in g]
    return jsonify(actors)


def actor_exist(name):
    return graph.cypher.execute_one("MATCH (a:Actor{name:{id}}) return 1", id=name) is not None


def movie_exists(title):
    return graph.cypher.execute_one("MATCH (m:Movie{title:{id}}) return 1", id=title) is not None


def director_exists(director):
    return graph.cypher.execute_one("MATCH (d:Director{name:{id}}) return 1", id=director) is not None


def get_node_id(node):
    if 'Movie' in node.labels:
        return node['title']
    return node['name']


def get_movie_count():
    return get_node_count('Movie')


def get_director_count():
    return get_node_count('Director')


def get_actor_count():
    return get_node_count('Actor')


def get_node_count(label):
    return graph.cypher.execute_one("MATCH (:{0}) RETURN count(*)".format(label))


def get_role_count():
    return graph.cypher.execute_one("MATCH ()-[:ACTS_IN]->(:Movie) return count(*)")

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

def get_node_label(node):
    if 'Movie' in node.labels:
        return 'Movie'
    elif 'Director' in node.labels and 'Actor' not in node.labels:
        return 'Director'
    return 'Actor'



def only_person(node):
    return 'Person' in node.labels and len(node.labels) == 1


from datetime import timedelta
from flask import make_response, request, current_app
from functools import update_wrapper

def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator


