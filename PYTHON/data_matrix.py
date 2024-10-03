import requests
import base64
import time
import json
import numpy as np
import random
import math

# Función para normalizar la matriz
def normalize_matrix(matrix):
    matrix = np.array(matrix)
    norm_matrix = np.zeros_like(matrix)
    for j in range(matrix.shape[1]):
        column = matrix[:, j]
        norm = np.linalg.norm(column)
        if norm == 0:
            norm_matrix[:, j] = column
        else:
            norm_matrix[:, j] = column / norm
    return norm_matrix

# Función para aplicar los pesos
def weight_matrix(matrix, weights):
    return matrix * weights

# Función para calcular las soluciones ideal y anti-ideal
def calculate_solutions(matrix):
    ideal = np.max(matrix, axis=0)
    anti_ideal = np.min(matrix, axis=0)

    # Ajuste para criterios de minimización (1, 5, 6)
    for j in [0, 4, 5]:
        ideal[j] = np.min(matrix[:, j])
        anti_ideal[j] = np.max(matrix[:, j])

    return ideal, anti_ideal

# Función para calcular las distancias euclidianas
def calculate_distance(alternative, solution):
    return np.linalg.norm(alternative - solution)

# Función para calcular las preferencias de las alternativas
def calculate_preferences(matrix, ideal, anti_ideal):
    preferences = []
    for alternative in matrix:
        distance_to_ideal = calculate_distance(alternative, ideal)
        distance_to_anti_ideal = calculate_distance(alternative, anti_ideal)
        preference = distance_to_anti_ideal / (distance_to_ideal + distance_to_anti_ideal)
        preferences.append(preference)
    return preferences

# Función para ordenar las alternativas
def sort_alternatives(preferences):
    alternatives = [{'index': i + 1, 'preference': pref} for i, pref in enumerate(preferences)]
    sorted_alts = sorted(alternatives, key=lambda x: x['preference'], reverse=True)
    return sorted_alts

# Función para reorganizar las alternativas cercanas
def reorganize_if_nearby(alternatives, threshold):
    nearby = [alternatives[0]]
    distances = [abs(alternatives[0]['preference'] - alt['preference']) for alt in alternatives[1:]]

    for i, distance in enumerate(distances):
        if distance < threshold:
            nearby.append(alternatives[i + 1])

    random.shuffle(nearby)
    reorganized = nearby + [alt for alt in alternatives if alt not in nearby]
    return reorganized

# Función principal
def main():
    
    start = time.time()
           
    # Lista de credenciales
    credentials = [
        {"url": "https://musing-haslett2.im.grycap.net", "user": "oscar", "password": "oscar123", "service": "grayifyr0"},
        {"url": "https://frosty-easley9.im.grycap.net", "user": "oscar", "password": "oscar123", "service": "grayifyr1"},
        {"url": "https://condescending-albattani4.im.grycap.net", "user": "oscar", "password": "oscar123", "service": "grayify"}
    ]

    service_cpu = 0.5
    results = []

    for cred in credentials:
        auth = base64.b64encode(f"{cred['user']}:{cred['password']}".encode()).decode()
        headers = {"Authorization": f"Basic {auth}"}

        try:
            # Realizar solicitud a /system/logs
            latency=0.0
            start_time=0.0
            url_jobs = f"{cred['url']}/system/logs/{cred['service']}"
            start_time = time.time()
            response = requests.get(url_jobs, headers=headers, verify=False, timeout=20)
            latency=time.time() - start_time
            
            

            job_statuses = response.json()

            total_jobs = 0
            succeeded_count = 0
            failed_count = 0
            pending_count = 0
            total_execution_time = 0

            for status in job_statuses.values():
                total_jobs += 1
                if status['status'] == 'Succeeded':
                    succeeded_count += 1
                    creation_time = time.strptime(status['creation_time'], "%Y-%m-%dT%H:%M:%SZ")
                    finish_time = time.strptime(status['finish_time'], "%Y-%m-%dT%H:%M:%SZ")
                    duration = time.mktime(finish_time) - time.mktime(creation_time)
                    total_execution_time += duration
                elif status['status'] == 'Failed':
                    failed_count += 1
                elif status['status'] == 'Pending':
                    pending_count += 1

            if succeeded_count > 0:
                average_execution_time = total_execution_time / succeeded_count
            else:
                average_execution_time = 0

            # Realizar solicitud a /system/status
            url_status = f"{cred['url']}/system/status"
            response = requests.get(url_status, headers=headers, verify=False, timeout=20)
            cluster_status = response.json()

            dist = cluster_status['cpuMaxFree'] - (1000 * service_cpu)

            if dist >= 0:
                result = [
                    latency,
                    cluster_status['numberNodes'],
                    cluster_status['memoryFreeTotal'],
                    cluster_status['cpuFreeTotal'],
                    average_execution_time,
                    pending_count + 0.1
                ]
            else:
                result = [20, 0, 0, 0, 1e6, 1e6]

            results.append(result)

        except requests.RequestException as e:
            print(f"Error fetching data for {cred['url']}: {e}")
            results.append([20, 0, 0, 0, 1e6, 1e6])

    # Pesos de los criterios
    weights = [1, 8, 18, 65, 2, 6]

    # Normalizar y ponderar la matriz de resultados
    print("Matriz de resultados:")
    for row in results:
        print(row)
    normalized_matrix = normalize_matrix(results)
    weighted_matrix = weight_matrix(normalized_matrix, weights)

    # Calcular solución ideal y anti-ideal
    ideal, anti_ideal = calculate_solutions(weighted_matrix)

    # Calcular preferencias
    preferences = calculate_preferences(weighted_matrix, ideal, anti_ideal)

    # Ordenar alternativas
    sorted_alternatives = sort_alternatives(preferences)
    for alt in sorted_alternatives:
        print(f"Alternativa {alt['index']}: {alt['preference']}")

    # Calcular el umbral y reorganizar si es necesario
    threshold = sorted_alternatives[0]['preference'] / 10
    reorganized_alternatives = reorganize_if_nearby(sorted_alternatives, threshold)

    # Mostrar resultados
    print("\nAlternativas reorganizadas:")
    for alt in reorganized_alternatives:
        print(f"Alternativa {alt['index']}: {alt['preference']}")

    print("\nTiempo de ejecución:", time.time() - start)

if __name__ == "__main__":
    main()
