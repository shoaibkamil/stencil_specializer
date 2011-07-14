"""Unrolls neighbor loops and InputElementZeroOffset nodes in a StencilModel.

The second stage in stencil kernel processing, after
stencil_python_front_end and before stencil_convert. This stage is
done once per call because the dimensions of the input are needed.
"""

from stencil_model import *
import ast
from assert_utils import *
from copy import deepcopy

class StencilUnrollNeighborIter(ast.NodeTransformer):
    def __init__(self, stencil_model, input_grids, output_grid):
        assert_has_type(stencil_model, StencilModel)
        assert len(input_grids) == len(stencil_model.input_grids), 'Incorrect number of input grids'
        self.model = stencil_model
        self.input_grids = input_grids
        self.output_grid = output_grid
        super(StencilUnrollNeighborIter, self).__init__()

    class NoNeighborIterChecker(ast.NodeVisitor):
        def __init__(self):
            super(StencilUnrollNeighborIter.NoNeighborIterChecker, self).__init__()

        def visit_StencilNeighborIter(self, node):
            assert False, 'Encountered StencilNeighborIter but all should have been removed'

        def visit_InputElementZeroOffset(self, node):
            assert False, 'Encountered InputElementZeroOffset but all should have been removed'

    def run(self):
        self.visit(self.model)
        StencilModelChecker().visit(self.model)
        StencilUnrollNeighborIter.NoNeighborIterChecker().visit(self.model)
        return self.model

    def visit_StencilModel(self, node):
        self.input_dict = dict()
        for i in range(len(node.input_grids)):
            self.input_dict[node.input_grids[i].name] = self.input_grids[i]
        self.generic_visit(node)

    def visit_Kernel(self, node):
        body = []
        for statement in node.body:
            if type(statement) is StencilNeighborIter:
                body.extend(self.visit_StencilNeighborIter_return_list(statement))
            else:
                body.append(self.visit(statement))
        return Kernel(body)

    def visit_StencilNeighborIter_return_list(self, node):
        grid = self.input_dict[node.grid.name]
        distance = node.distance.value
        zero_point = tuple([0 for x in range(grid.dim)])
        result = []
        self.current_neighbor_grid_id = node.grid
        for x in grid.neighbors(zero_point, distance):
            self.offset_list = list(x)
            for statement in node.body:
                result.append(self.visit(deepcopy(statement)))
        self.offset_list = None
        self.current_neighbor_grid = None
        return result

    def visit_Neighbor(self, node):
        return InputElement(self.current_neighbor_grid_id, self.offset_list)

    def visit_InputElementZeroOffset(self, node):
        grid = self.input_dict[node.grid.name]
        zero_point = tuple([0 for x in range(grid.dim)])
        return InputElement(node.grid, zero_point)
