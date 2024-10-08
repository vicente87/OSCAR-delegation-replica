import requests
import base64
import time
import json
import numpy as np
import random
import math



def mapRange(value, min_input, max_input, max_output, min_output):
    # Calcular el valor mapeado
    mapped_value = max_output - (max_output - min_output) * (value - min_input) / (max_input - min_input)
    
    # Convertir el valor mapeado a entero
    mapped_int = int(mapped_value)

    # Asegurarse de que el valor mapeado esté dentro del rango
    if mapped_int > max_output:
        mapped_int = int(max_output)
    if mapped_int < min_output:
        mapped_int = int(min_output)

    return mapped_int
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

def jobs_status (job_statuses):
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
    return average_execution_time,pending_count

def get_headers(cred):
    if 'token' in cred and cred['token']:
        headers = {'Authorization': "Bearer " + cred['token'] }

    elif 'user' in cred and cred['user'] and 'password' in cred and cred['password']:
        auth = base64.b64encode(f"{cred['user']}:{cred['password']}".encode()).decode()
        headers = {"Authorization": f"Basic {auth}"}
    else:
        print(f"Error with credentials to {cred['url']}")
        headers = {"Authorization": ""}
    return headers 

def main():
    delegation= "topsis"
    credentials = [
        {"url": "https://musing-haslett2.im.grycap.net", "user": "oscar", "password": "oscar123","token":"", "service": "grayifyr0","priority":2},
        {"url": "https://frosty-easley9.im.grycap.net", "user": "oscar", "password": "oscar123","token":"", "service": "grayifyr1","priority":3},
        {"url": "https://condescending-albattani4.im.grycap.net", "user": "oscar", "password": "oscar123","token":"", "service": "grayify", "priority":1}
    ]
    
    final_delegation = [{"url": "", "user": "", "password": "", "token": "", "service": "", "priority": None} for _ in credentials]
    

    noDelegateCode=101
    results=[]
    
    for i, cred in enumerate(credentials):
        
        headers=get_headers(cred)

        try:
            url_service = f"{cred['url']}/system/services/{cred['service']}"
            response = requests.get(url_service, headers=headers, verify=False, timeout=20)
            cluster_service = response.json()
            cpu_service=float(cluster_service['cpu'])
            
            
            # Realizar solicitud a /system/logs
            url_status = f"{cred['url']}/system/status"
            response = requests.get(url_status, headers=headers, verify=False, timeout=20)
            cluster_status = response.json()
            

            dist = cluster_status['cpuMaxFree'] - (1000 * cpu_service)
                        
            if dist >= 0:
                if delegation=="static":
                    print("Ordenado por priority manual")
                elif delegation =="random":
                    rand_priority = random.randint(1, noDelegateCode - 1)
                    credentials[i]["priority"]=rand_priority
                    print("ordenado random de priority")
                elif delegation =="load_based":
                    totalClusterCPU = cluster_status['cpuFreeTotal']
                    print(totalClusterCPU)
                    mappedCPUPriority = mapRange(totalClusterCPU, 0, 4000, 100, 0)
                    credentials[i]["priority"]=mappedCPUPriority
                elif delegation =="topsis":
                    latency=0.0
                    start_time=0.0
                    url_jobs = f"{cred['url']}/system/logs/{cred['service']}"
                    start_time = time.time()
                    response = requests.get(url_jobs, headers=headers, verify=False, timeout=20)
                    latency=time.time() - start_time
             
                    job_statuses = response.json()
                    
                    average_execution_time,pending_count =jobs_status(job_statuses)

                    result = [
                    latency,
                    cluster_status['numberNodes'],
                    cluster_status['memoryFreeTotal'],
                    cluster_status['cpuFreeTotal'],
                    average_execution_time,
                    pending_count + 0.1
                    ]
                    results.append(result)
                
            else:
                if delegation !="static":
                    credentials[i]["priority"]=noDelegateCode
                elif delegation =="topsis":
                    result = [20, 0, 0, 0, 1e6, 1e6]
                    results.append(result)

               

        except requests.RequestException as e:
            if delegation =="topsis":
                result = [20, 0, 0, 0, 1e6, 1e6]
                results.append(result)
            elif delegation =="random" or delegation =="load_based":
                credentials[i]["priority"]=noDelegateCode
            print(f"Error fetching data for {cred['url']}: {e}")

    
    if delegation =="topsis":
        weights = [1, 8, 18, 65, 2, 6]

    # Normalizar y ponderar la matriz de resultados
        print("Matriz de resultados:")
        
        normalized_matrix = normalize_matrix(results)
        weighted_matrix = weight_matrix(normalized_matrix, weights)

    # Calcular solución ideal y anti-ideal
        ideal, anti_ideal = calculate_solutions(weighted_matrix)

    # Calcular preferencias
        preferences = calculate_preferences(weighted_matrix, ideal, anti_ideal)
        sorted_alternatives = sort_alternatives(preferences)
        
        
    # Calcular el umbral y reorganizar si es necesario
        threshold = sorted_alternatives[0]['preference'] / 3
        reorganized_alternatives = reorganize_if_nearby(sorted_alternatives, threshold) 
        print("Alternativas: ")
        for row in reorganized_alternatives:
            print(row)
        print("\nAlternativas reorganizadas:")
        for i,alt in enumerate(reorganized_alternatives):
            mappedCPUPriority = mapRange(alt['preference'], 0, 1, 100, 0)
            print(f"Alternativa {alt['index']}: {alt['preference']} : {mappedCPUPriority}")
            credentials[alt['index']-1]["priority"]=mappedCPUPriority
            final_delegation[i]=credentials[alt['index']-1]
            
            
    credentials=final_delegation
    #credentials.sort(key=lambda cred: cred['priority'])
    print("Replicas Stable: ", credentials)

    print("Imagen a procesar")
    dir_img="image-orig_1.jpg"
   # img = mpimg.imread(dir_img)
    #plt.imshow(img)  

    with open(dir_img, 'rb') as binary_file:
        binary_file_data = binary_file.read()
        base64_encoded_data = base64.b64encode(binary_file_data)
        base64_message = base64_encoded_data.decode('utf-8')
        my_string = base64_message

    
    

    # Peticion POST
    for i, cluster in enumerate(credentials):

        headers=get_headers(cluster)

        url_service = f"{cluster['url']}/system/services/{cluster['service']}"
        
        url_run = f"{cluster['url']}/job/{cluster['service']}"
        try:
            response = requests.get(url_service, headers=headers, verify=False, timeout=20)
            cluster_service = response.json()
            token_service=cluster_service['token']
            
            headers = {    
                'Authorization': "Bearer " + token_service,
                'Content-Type': 'application/json',
            }
            
            response = requests.post(url_run, headers=headers, data=my_string,verify=False, timeout=20)
            
            if response.status_code == 200 or response.status_code == 201:
                print(f"Services OK to {cluster['url']}")
                ## ver la respuesta o no
                """
                texto=response.text
                print(response.json)
                inicio=texto.find('response')
                img_data=texto[inicio+9:]
                image_64_decode = base64.b64decode(img_data)

#image_64_decode = base64.decodestring(img_data) 
                image_result = open('decode.jpg', 'wb') # create a writable image and write the decoding result
                image_result.write(image_64_decode)
                image_result.close()
                """
                break
                
            else:
                print(response.status_code)
          #print(response.text)
        except Exception as ex:
            print(f"Error running service in {cluster['url']} : {ex}")
    
if __name__ == "__main__":
    main()
            

