import requests
import cirq
import sys

#root = 'http://127.0.0.1:8080'
root = sys.argv[1]

qubits = cirq.LineQubit.range(2)

circuit = cirq.Circuit(
    cirq.H(qubits[0]),
    cirq.X(qubits[1])**0.5, 
    cirq.CX(*qubits),
    cirq.measure(*qubits)
    )
print(circuit.to_qasm())

print(requests.post(root + "/send", json={"qasm":circuit.to_qasm(), "email":"test4", "shots":3}).text) 
print(requests.get(root + "/lookup", params={"jid":sys.argv[2]}).text) 
