import requests
import cirq
import sys
from cirq.google import optimized_for_sycamore

root = sys.argv[1]

qubits = cirq.LineQubit.range(2)

circuit = cirq.Circuit(
    cirq.H(qubits[0]),
    cirq.X(qubits[1])**0.5, 
    cirq.CX(*qubits),
    cirq.measure(*qubits)
    )
print(circuit)
print(circuit.to_qasm())

print(requests.post(root + "send", json={"qasm":circuit.to_qasm(), "email":"test4", "repetitions":3, "student_id":1234, 'note':'test note'}).text)
print(requests.post(root + "send", json={"qasm":circuit.to_qasm(), "email":"test4", "repetitions":3, "student_id":1234}).text) 
print(requests.post(root + "send", json={"qasm":circuit.to_qasm(), "email":"test4", "repetitions":3, "student_id":1234}).text) 
