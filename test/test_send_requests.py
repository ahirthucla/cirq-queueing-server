import requests
import cirq
import sys
from cirq.google import optimized_for_sycamore

root = sys.argv[1]

qubits = cirq.GridQubit.square(3)
circuits = [cirq.testing.random_circuit(qubits, 10, 0.6) for _ in range(25)]
for circuit in circuits:
    circuit.append(cirq.measure_each(*qubits))
qubits = cirq.LineQubit.range(9)
circuits2 = [cirq.testing.random_circuit(qubits, 10, .6) for _ in range(25)]
for circuit in circuits2:
    circuit.append(cirq.measure_each(*qubits))
circuits = circuits + circuits2

print(len(circuits))
for circuit in circuits:
    print(requests.post(root + "send", json={"circuit":cirq.to_json(circuit), "email":"test5", "repetitions":5, "student_id":5}).text)
