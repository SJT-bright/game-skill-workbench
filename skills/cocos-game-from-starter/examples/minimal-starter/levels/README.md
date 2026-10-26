# Corridor layout and solution format

Each layout records start, target and length. Actions are right moves, one cell per action. Solutions bind exact layout SHA. A receiver can replay actions and verify final position equals target and each intermediate position is inside [0,length). The production game must supply its own real rules and useful level variety; these simple fixtures only illustrate the contract.
