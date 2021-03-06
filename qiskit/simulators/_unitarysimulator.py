# -*- coding: utf-8 -*-

# Copyright 2017 IBM RESEARCH. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

"""Contains a (slow) Python simulator that returns the unitary of the circuit.

It simulates a unitary of a quantum circuit that has been compiled to run on
the simulator. It is exponential in the number of qubits.

The input is the circuit object and the output is the same circuit object with
a result field added results['data']['unitary'] where the unitary is
a 2**n x 2**n complex numpy array representing the unitary matrix.


The input is

    compiled_circuit object

and the output is the results object

The simulator is run using

    UnitarySimulator(compiled_circuit).run().

In the qasm, key operations with type 'measure' and 'reset' are dropped.

Internal circuit_object::

    compiled_circuit =
    {
     "header": {
     "number_of_qubits": 2, // int
     "number_of_clbits": 2, // int
     "qubit_labels": [["q", 0], ["v", 0]], // list[list[string, int]]
     "clbit_labels": [["c", 2]], // list[list[string, int]]
     }
     "operations": // list[map]
        [
            {
                "name": , // required -- string
                "params": , // optional -- list[double]
                "qubits": , // required -- list[int]
                "clbits": , //optional -- list[int]
                "conditional":  // optional -- map
                    {
                        "type": , // string
                        "mask": , // hex string 
                        "val":  , // bhex string 
                    }
            },
        ]
    }

returned results object::

    result =
            {
            'data':
                {
                'unitary': np.array([[ 0.70710678 +0.00000000e+00j
                                     0.70710678 -8.65956056e-17j
                                     0.00000000 +0.00000000e+00j
                                     0.00000000 +0.00000000e+00j]
                                   [ 0.00000000 +0.00000000e+00j
                                     0.00000000 +0.00000000e+00j
                                     0.70710678 +0.00000000e+00j
                                     -0.70710678 +8.65956056e-17j]
                                   [ 0.00000000 +0.00000000e+00j
                                     0.00000000 +0.00000000e+00j
                                     0.70710678 +0.00000000e+00j
                                     0.70710678 -8.65956056e-17j]
                                   [ 0.70710678 +0.00000000e+00j
                                    -0.70710678 +8.65956056e-17j
                                     0.00000000 +0.00000000e+00j
                                     0.00000000 +0.00000000e+00j]
                }
            'state': 'DONE'
            }
"""
import numpy as np
from ._simulatortools import enlarge_single_opt, enlarge_two_opt, single_gate_matrix
import json
# TODO add ["status"] = 'DONE', 'ERROR' especitally for empty circuit error
# does not show up

__configuration = {"name": "local_unitary_simulator",
                   "url": "https://github.com/IBM/qiskit-sdk-py",
                   "simulator": True,
                   "description": "A python simulator for unitary matrix",
                   "coupling_map": "all-to-all",
                   "basis_gates": "u1,u2,u3,cx,id"}


class UnitarySimulator(object):
    """Python implementation of a unitary simulator."""

    def __init__(self, job):
        """Initial the UnitarySimulator object."""
        self.circuit = json.loads(job['compiled_circuit'].decode())
        self._number_of_qubits = self.circuit['header']['number_of_qubits']
        self.result = {}
        self.result = {}
        self.result['data'] = {}
        self._unitary_state = np.identity(2**(self._number_of_qubits),
                                          dtype=complex)
        self._number_of_operations = len(self.circuit['operations'])

    def _add_unitary_single(self, gate, qubit):
        """Apply the single-qubit gate.

        gate is the single-qubit gate.
        qubit is the qubit to apply it on counts from 0 and order
            is q_{n-1} ... otimes q_1 otimes q_0.
        number_of_qubits is the number of qubits in the system.
        """
        unitaty_add = enlarge_single_opt(gate, qubit, self._number_of_qubits)
        self._unitary_state = np.dot(unitaty_add, self._unitary_state)

    def _add_unitary_two(self, gate, q0, q1):
        """Apply the two-qubit gate.

        gate is the two-qubit gate
        q0 is the first qubit (control) counts from 0
        q1 is the second qubit (target)
        returns a complex numpy array
        """
        unitaty_add = enlarge_two_opt(gate, q0, q1, self._number_of_qubits)
        self._unitary_state = np.dot(unitaty_add, self._unitary_state)

    def run(self, silent=True):
        """Apply the single-qubit gate."""
        for operation in self.circuit['operations']:
            if operation['name'] in ['U', 'u1', 'u2', 'u3']:
                if 'params' in operation:
                    params = operation['params']
                else:
                    params = None
                qubit = operation['qubits'][0]
                gate = single_gate_matrix(operation['name'], params)
                self._add_unitary_single(gate, qubit)
            elif operation['name'] in ['id', 'u0']:
                pass
            elif operation['name'] in ['CX', 'cx']:
                qubit0 = operation['qubits'][0]
                qubit1 = operation['qubits'][1]
                gate = np.array([[1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0],
                                 [0, 1, 0, 0]])
                self._add_unitary_two(gate, qubit0, qubit1)
            elif operation['name'] == 'measure':
                if silent is False:
                    print('Warning have dropped measure from unitary simulator')
            elif operation['name'] == 'reset':
                if silent is False:
                    print('Warning have dropped reset from unitary simulator')
            elif operation['name'] == 'barrier':
                pass
            else:
                self.result['status'] = 'ERROR'
                return self.result
        self.result['data']['unitary'] = self._unitary_state
        self.result['status'] = 'DONE'
        return self.result
