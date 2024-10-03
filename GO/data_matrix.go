package main

import (
	"crypto/tls"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"math/rand"
	"net/http"
	"sort"
	"strconv"
	"time"
)

// Credenciales representa las credenciales para una URL específica
type Credencials struct {
	URL      string
	Usuario  string
	Password string
	Service  string
}

type GeneralInfo struct {
	NumberNodes     int64      `json:"numberNodes"`
	CPUFreeTotal    int64      `json:"cpuFreeTotal"`
	CPUMaxFree      int64      `json:"cpuMaxFree"`
	MemoryFreeTotal int64      `json:"memoryFreeTotal"`
	MemoryMaxFree   int64      `json:"memoryMaxFree"`
	DetailsNodes    []NodeInfo `json:"detail"`
}

type NodeInfo struct {
	NodeName         string `json:"nodeName"`
	CPUCapacity      string `json:"cpuCapacity"`
	CPUUsage         string `json:"cpuUsage"`
	CPUPercentage    string `json:"cpuPercentage"`
	MemoryCapacity   string `json:"memoryCapacity"`
	MemoryUsage      string `json:"memoryUsage"`
	MemoryPercentage string `json:"memoryPercentage"`
}

type Alternative struct {
	Index      int     // Número de la alternativa
	Preference float64 // Valor de la preferencia
}

type JobStatus struct {
	Status       string `json:"status"`
	CreationTime string `json:"creation_time"`
	StartTime    string `json:"start_time"`
	FinishTime   string `json:"finish_time"`
}
type JobStatuses map[string]JobStatus

// Normaliza una columna dividiendo cada valor por la raíz cuadrada de la suma de cuadrados.
func normalizeMatrix(matrix [][]float64) [][]float64 {
	rows := len(matrix)
	cols := len(matrix[0])
	normalized := make([][]float64, rows)
	for i := range normalized {
		normalized[i] = make([]float64, cols)
	}

	for j := 0; j < cols; j++ {
		// Calcular la norma (raíz cuadrada de la suma de cuadrados de la columna)
		add := 0.0
		for i := 0; i < rows; i++ {
			add += matrix[i][j] * matrix[i][j]
		}
		norma := math.Sqrt(add)
		// Normalizar los valores de la columna
		for i := 0; i < rows; i++ {
			normalized[i][j] = matrix[i][j] / norma
		}
	}
	return normalized
}

// Multiplica la matriz normalizada por los pesos.
func weightMatrix(matrix [][]float64, weight []float64) [][]float64 {
	rows := len(matrix)
	cols := len(matrix[0])
	weighted := make([][]float64, rows)
	for i := range weighted {
		weighted[i] = make([]float64, cols)
		for j := 0; j < cols; j++ {
			weighted[i][j] = matrix[i][j] * weight[j]
		}
	}
	return weighted
}

// Calcula la solución ideal y anti-ideal.
func calculateSolutions(matrix [][]float64) (ideal []float64, antiIdeal []float64) {
	rows := len(matrix)
	cols := len(matrix[0])

	ideal = make([]float64, cols)
	antiIdeal = make([]float64, cols)

	for j := 0; j < cols; j++ {
		// Si el criterio es de minimización (supongamos que el primer criterio es el que queremos minimizar)

		if j == 0 || j == 4 || j == 5 {
			// Para la solución ideal, seleccionamos el valor mínimo (en lugar del máximo)
			ideal[j] = matrix[0][j]
			antiIdeal[j] = matrix[0][j]
			for i := 0; i < rows; i++ {
				if matrix[i][j] < ideal[j] {
					ideal[j] = matrix[i][j]
				}
				if matrix[i][j] > antiIdeal[j] {
					antiIdeal[j] = matrix[i][j]
				}
			}
		} else {
			// Para los criterios de maximización, usamos los valores máximos y mínimos normalmente
			ideal[j] = matrix[0][j]
			antiIdeal[j] = matrix[0][j]
			for i := 0; i < rows; i++ {
				if matrix[i][j] > ideal[j] {
					ideal[j] = matrix[i][j]
				}
				if matrix[i][j] < antiIdeal[j] {
					antiIdeal[j] = matrix[i][j]
				}
			}
		}
	}
	return ideal, antiIdeal
}

// Calcula la distancia euclidiana entre una alternativa y la solución ideal o anti-ideal.
func calculateDistance(alternative []float64, solution []float64) float64 {
	add := 0.0
	for i := 0; i < len(alternative); i++ {
		add += (alternative[i] - solution[i]) * (alternative[i] - solution[i])
	}
	return math.Sqrt(add)
}

// Calcula el índice de preferencia para cada alternativa.
func calculatePreferences(matrix [][]float64, ideal []float64, antiIdeal []float64) []float64 {
	rows := len(matrix)
	preferences := make([]float64, rows)

	for i := 0; i < rows; i++ {
		distanceIdeal := calculateDistance(matrix[i], ideal)
		distanceAntiIdeal := calculateDistance(matrix[i], antiIdeal)
		preferences[i] = distanceAntiIdeal / (distanceIdeal + distanceAntiIdeal)
	}
	return preferences
}

// Ordena las alternativas de mejor a peor según el índice de preferencia.
func sortAlternatives(preferences []float64) []Alternative {
	alternatives := make([]Alternative, len(preferences))

	// Crear una lista de alternativas con sus índices de preferencia
	for i := 0; i < len(preferences); i++ {
		alternatives[i] = Alternative{
			Index:      i + 1, // Alternativa 1, 2, etc.
			Preference: preferences[i],
		}
	}

	// Ordenar las alternativas en orden descendente de preferencia
	sort.Slice(alternatives, func(i, j int) bool {
		return alternatives[i].Preference > alternatives[j].Preference
	})

	return alternatives
}

func mapToRange(value, minInput, maxInput, maxOutput, minOutput int64) int {
	mappedValue := maxOutput - (maxOutput-minOutput)*(value-minInput)/(maxInput-minInput)
	mappedInt := int(mappedValue)
	if mappedInt > int(maxOutput) {
		mappedInt = int(maxOutput)
	}
	if mappedInt < int(minOutput) {
		mappedInt = int(minOutput)
	}

	return mappedInt
}

func distancesFromBetter(alternatives []Alternative) []float64 {
	distances := make([]float64, len(alternatives)-1)

	// Calcular distancias con el primer elemento
	for i := 1; i < len(alternatives); i++ {
		distances[i-1] = math.Abs(alternatives[0].Preference - alternatives[i].Preference)
	}

	return distances
}

// Función para reorganizar aleatoriamente los elementos cuya distancia con el primero es menor a un umbral, incluyendo el primero.
func reorganizeIfNearby(alternatives []Alternative, distances []float64, threshold float64) []Alternative {
	// Lista de elementos cercanos (con distancia menor al umbral, incluyendo el primer elemento)
	nearby := []Alternative{alternatives[0]} // Incluir el primer elemento en la lista

	// Identificar los demás elementos cercanos
	for i := 0; i < len(distances); i++ {
		if distances[i] < threshold {
			nearby = append(nearby, alternatives[i+1]) // i+1 porque el primer elemento es el 0
		}
	}

	// Barajar (mezclar aleatoriamente) los elementos cercanos
	//rand.Seed(time.Now().UnixNano())
	rand.Shuffle(len(nearby), func(i, j int) {
		nearby[i], nearby[j] = nearby[j], nearby[i]
	})

	// Crear una nueva lista de alternativas reorganizada
	newAlternatives := []Alternative{}
	j := 0

	// Insertar los elementos reorganizados o no
	for i := 0; i < len(alternatives); i++ {
		if i == 0 || distances[i-1] < threshold {
			newAlternatives = append(newAlternatives, nearby[j]) // Agregar los elementos reorganizados
			j++
		} else {
			newAlternatives = append(newAlternatives, alternatives[i]) // Mantener los elementos no cercanos
		}
	}

	return newAlternatives
}

func main() {
	// Lista de credenciales para cada URL
	time_exec := time.Now()

	credentials := []Credencials{
		{URL: "https://musing-haslett2.im.grycap.net", Usuario: "oscar", Password: "oscar123", Service: "grayifyr0"},
		{URL: "https://frosty-easley9.im.grycap.net", Usuario: "oscar", Password: "oscar123", Service: "grayifyr1"},
		{URL: "https://condescending-albattani4.im.grycap.net", Usuario: "oscar", Password: "oscar123", Service: "grayify"},
	}

	ServiceCPU := "0.5"
	// Matriz para almacenar los resultados
	results := [][]float64{}

	for _, cred := range credentials {
		// Codificar las credenciales en base64
		auth := base64.StdEncoding.EncodeToString([]byte(cred.Usuario + ":" + cred.Password))

		// Crear una nueva solicitud GET con la URL
		// Crear una nueva solicitud GET con la URL
		url_jobs := cred.URL + "/system/logs/" + cred.Service

		req, err := http.NewRequest("GET", url_jobs, nil)
		if err != nil {
			fmt.Printf("Error al crear la solicitud para %s: %v\n", cred.URL, err)
			results = append(results, []float64{20, 0, 0, 0, 1e6, 1e6})
			continue
		}

		// Agregar el encabezado de autorización con las credenciales
		req.Header.Add("Authorization", "Basic "+auth)

		// Realizar la solicitud HTTP
		SSLVerify := false
		var transport http.RoundTripper = &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: !SSLVerify},
		}
		client := &http.Client{
			Transport: transport,
			Timeout:   time.Second * 20,
		}
		resp, err := client.Do(req)
		if err != nil {
			fmt.Printf("Error al realizar la solicitud para %s: %v\n", cred.URL, err)
			results = append(results, []float64{20, 0, 0, 0, 1e6, 1e6})
			continue
		}

		defer resp.Body.Close()
		body, err := io.ReadAll(resp.Body) // Utilizar io.ReadAll para leer el cuerpo
		if err != nil {
			fmt.Printf("Error al leer el cuerpo de la respuesta para %s: %v\n", cred.URL, err)
			results = append(results, []float64{20, 0, 0, 0, 1e6, 1e6})
			return
		}

		// Imprimir el cuerpo de la respuesta como una cadena
		//fmt.Println("Cuerpo de la respuesta:")
		//fmt.Println(string(body)) // Convertir a string y mostrar

		var jobStatuses JobStatuses
		err = json.Unmarshal(body, &jobStatuses)
		if err != nil {
			fmt.Println("Error decoding the JSON of the response:", err)
			results = append(results, []float64{20, 0, 0, 0, 1e6, 1e6})
			continue
		}

		// Mostrar los estados de los trabajos
		totalJobs := 0
		succeededCount := 0
		failedCount := 0
		pendingCount := 0
		totalExecutionTime := 0.0

		// Contar los estados de los trabajos
		for _, status := range jobStatuses {
			totalJobs++
			switch status.Status {
			case "Succeeded":
				succeededCount++
				creationTime, _ := time.Parse(time.RFC3339, status.CreationTime)
				finishTime, _ := time.Parse(time.RFC3339, status.FinishTime)
				duration := finishTime.Sub(creationTime).Seconds() // Duración en segundos
				totalExecutionTime += duration
			case "Failed":
				failedCount++
			case "Pending":
				pendingCount++
			}
		}

		var averageExecutionTime float64
		if succeededCount > 0 {
			averageExecutionTime = totalExecutionTime / float64(succeededCount)
		}
		url_status := cred.URL + "/system/status"
		req1, err := http.NewRequest("GET", url_status, nil)
		if err != nil {
			fmt.Printf("Error al crear la solicitud para %s: %v\n", cred.URL, err)
			results = append(results, []float64{20, 0, 0, 0, 1e6, 1e6})
			continue
		}

		// Agregar el encabezado de autorización con las credenciales
		req1.Header.Add("Authorization", "Basic "+auth)

		// Realizar la solicitud HTTP

		start := time.Now()
		resp1, err := client.Do(req1)
		duration := time.Since(start)
		if err != nil {
			fmt.Printf("Error al realizar la solicitud para %s: %v\n", cred.URL, err)
			results = append(results, []float64{duration.Seconds(), 0, 0, 0, 1e6, 1e6})
			continue
		}

		defer resp1.Body.Close()
		var clusterStatus GeneralInfo
		err = json.NewDecoder(resp1.Body).Decode(&clusterStatus)
		if err != nil {
			fmt.Println("Error decoding the JSON of the response:", err)
			results = append(results, []float64{duration.Seconds(), 0, 0, 0, 1e6, 1e6})
			continue
		}

		serviceCPU, err := strconv.ParseFloat(ServiceCPU, 64)
		if err != nil {
			fmt.Println("Error converting service CPU to float: ", err)
			results = append(results, []float64{duration.Seconds(), 0, 0, 0, 1e6, 1e6})
			continue
		}

		maxNodeCPU := float64(clusterStatus.CPUMaxFree)
		dist := maxNodeCPU - (1000 * serviceCPU)

		if dist >= 0 {
			results = append(results, []float64{
				duration.Seconds(),                     // Latency (ms)
				float64(clusterStatus.NumberNodes),     // Number of nodes
				float64(clusterStatus.MemoryFreeTotal), // Total Memory Free
				float64(clusterStatus.CPUFreeTotal),    // Total CPU Free
				averageExecutionTime,                   // averageExecutionTime
				float64(pendingCount) + 0.1,            //pendingCount
				// Aquí puedes agregar más criterios si es necesario
			})
		} else {
			results = append(results, []float64{duration.Seconds(), 0, 0, 0, 1e6, 1e6})
		}
	}

	// Imprimir resultados en la forma de matriz
	fmt.Println("Matriz de resultados:")
	for _, row := range results {
		fmt.Println(row)
	}
	// Pesos de los criterios (iguales en este caso).
	weight := []float64{1, 8, 18, 65, 2, 6}

	// Paso 1: Normalizar la matriz
	matrixNormalized := normalizeMatrix(results)
	//fmt.Println("Matriz Normalizada:")
	//for _, row := range matrizNormalizada {
	//	fmt.Println(row)
	//}

	// Paso 2: Ponderar la matriz
	matrixWeighted := weightMatrix(matrixNormalized, weight)
	//fmt.Println("\nMatriz Ponderada:")
	//for _, row := range matrizPonderada {
	//	fmt.Println(row)
	//}

	// Paso 3: Calcular la solución ideal y anti-ideal
	ideal, antiIdeal := calculateSolutions(matrixWeighted)
	//fmt.Println("\nSolución Ideal:", ideal)
	//fmt.Println("Solución Anti-Ideal:", antiIdeal)

	// Paso 4: Calcular las distancias y el índice de preferencia
	preferences := calculatePreferences(matrixWeighted, ideal, antiIdeal)
	fmt.Println("\nÍndices de Preferencia:", preferences)

	// Paso 5: Ordenar alternativas de mejor a peor
	alternativesSort := sortAlternatives(preferences)

	fmt.Println("\nAlternativas ordenadas de mejor a peor:")
	for _, alt := range alternativesSort {
		fmt.Printf("Alternativa %d: %f\n", alt.Index, alt.Preference)

		//mapped := mapToRange(int64(alt*100.0), 0, 100, 100, 0)
		//fmt.Printf("Preferencia original: %.4f -> Mapeada: %d\n", alt, mapped)
	}
	distancesFromBetter := distancesFromBetter(alternativesSort)

	// Umbral para reorganizar los elementos cercanos
	threshold := alternativesSort[0].Preference / 10.0
	fmt.Println("El umbral es el 10% del mejor valor : ", threshold)

	// Reorganizar aleatoriamente los elementos cuya distancia sea menor que el umbral, incluyendo el primero
	newAlternatives := reorganizeIfNearby(alternativesSort, distancesFromBetter, threshold)

	// Imprimir alternativas reorganizadas
	fmt.Println("\nAlternativas reorganizadas por umbral:")
	for _, alt := range newAlternatives {
		fmt.Printf("Alternativa %d: %f\n", alt.Index, alt.Preference)
	}
	duration_exec := time.Since(time_exec)
	fmt.Println("Tiempo de ejecucion del algoritmo : ", duration_exec.Milliseconds())

}
