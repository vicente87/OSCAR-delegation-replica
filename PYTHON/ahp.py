import numpy as np

def normalize_matrix(matrix):
    # Suma de las columnas
    column_sums = np.sum(matrix, axis=0)
    # Normalizar la matriz dividiendo cada elemento por la suma de su columna
    normalized_matrix = matrix / column_sums
    return normalized_matrix

def calculate_weights(normalized_matrix):
    # Sumar cada fila de la matriz normalizada y dividir por el número de criterios
    row_averages = np.mean(normalized_matrix, axis=1)
    return row_averages

def ahp(criteria_matrix):
    # Paso 1: Normalizar la matriz de comparación
    normalized_matrix = normalize_matrix(criteria_matrix)
    print("Matriz Normalizada:")
    print(normalized_matrix)
    
    # Paso 2: Calcular los pesos
    weights = calculate_weights(normalized_matrix)
    return weights

if __name__ == "__main__":
    # Matriz de comparación por pares (ejemplo: Rentabilidad, Riesgo, Liquidez)
    criteria_matrix = np.array([
        [1,1/8,1/9,1/8,1/2,1/3,],   # Rentabilidad (R)
        [8,1,1/7,1/3,5,6], # Riesgo (Ri)
        [9,7,1,6,9,8],
        [8,3,1/6,1,6,4],
        [2,1/5,1/9,1/6,1,1/2],
        [3,1/6,1/8,1/4,2,1]# Liquidez (L)
    ])
    
    # Ejecutar el algoritmo AHP
    weights = ahp(criteria_matrix)
    
    # Mostrar los pesos finales
    print("\nPesos finales de los criterios:")
    for i, weight in enumerate(weights):
        print(f"Criterio {i+1}: {weight:.4f}")
