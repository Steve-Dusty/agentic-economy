"""
Gateway Step Handler

Handles gateway (conditional routing) steps by evaluating
conditions and determining which route to take.

Reference: BACKLOG_CORE.md - E7-01, E7-02
"""

import logging
from typing import Any, Optional

from ...domain import StepType, GatewayConfig
from ...services import ConditionEvaluator, EvaluationContext
from ..step_handler import StepHandler, StepResult, StepContext, StepConfig


logger = logging.getLogger(__name__)


class GatewayHandler(StepHandler):
    """
    Handler for gateway step type.
    
    Evaluates conditions and routes to the appropriate next step(s).
    
    Gateway Types:
    - exclusive (XOR): First matching condition wins
    - parallel: All matching conditions execute (future)
    - inclusive: All matching conditions OR default (future)
    
    For MVP, only exclusive gateways are fully supported.
    """
    
    def __init__(self):
        """Initialize handler with condition evaluator."""
        self.condition_evaluator = ConditionEvaluator()
    
    @property
    def step_type(self) -> StepType:
        return StepType.GATEWAY
    
    async def execute(
        self,
        context: StepContext,
        config: StepConfig,
    ) -> StepResult:
        """
        Execute a gateway step.
        
        Evaluates conditions in order and outputs the chosen route.
        Downstream steps can check the gateway output to determine
        if they should run.
        """
        if not isinstance(config, GatewayConfig):
            return StepResult.fail(
                f"Invalid config type: {type(config).__name__}",
                error_code="INVALID_CONFIG",
            )
        
        gateway_type = config.gateway_type
        routes = config.routes
        default_route = config.default_route
        
        logger.info(
            f"Evaluating gateway (type={gateway_type}, "
            f"routes={len(routes)}, default={default_route})"
        )
        
        # Build evaluation context from execution state
        eval_context = EvaluationContext(
            input_data=context.execution.input_data,
            step_outputs=context.step_outputs,
            execution_id=str(context.execution.id),
            process_name=context.execution.process_name,
        )
        
        # Evaluate routes based on gateway type
        if gateway_type == "exclusive":
            return self._evaluate_exclusive(routes, default_route, eval_context)
        elif gateway_type == "parallel":
            return self._evaluate_parallel(routes, default_route, eval_context)
        elif gateway_type == "inclusive":
            return self._evaluate_inclusive(routes, default_route, eval_context)
        else:
            return StepResult.fail(
                f"Unknown gateway type: {gateway_type}",
                error_code="INVALID_GATEWAY_TYPE",
            )
    
    def _evaluate_exclusive(
        self,
        routes: list[dict],
        default_route: Optional[str],
        context: EvaluationContext,
    ) -> StepResult:
        """
        Evaluate exclusive (XOR) gateway.
        
        First matching condition wins.
        """
        evaluated_conditions = []
        
        for route in routes:
            condition = route.get("condition", "")
            target = route.get("target")
            
            if not target:
                logger.warning(f"Route without target: {route}")
                continue
            
            try:
                result = self.condition_evaluator.evaluate(condition, context)
                evaluated_conditions.append({
                    "condition": condition,
                    "target": target,
                    "result": result,
                })
                
                if result:
                    logger.info(f"Gateway routed to '{target}' (condition: {condition})")
                    return StepResult.ok({
                        "route": target,
                        "condition": condition,
                        "gateway_type": "exclusive",
                        "evaluated_conditions": evaluated_conditions,
                    })
                    
            except Exception as e:
                logger.error(f"Error evaluating condition '{condition}': {e}")
                evaluated_conditions.append({
                    "condition": condition,
                    "target": target,
                    "result": False,
                    "error": str(e),
                })
        
        # No condition matched - use default
        if default_route:
            logger.info(f"Gateway using default route: {default_route}")
            return StepResult.ok({
                "route": default_route,
                "condition": None,
                "gateway_type": "exclusive",
                "is_default": True,
                "evaluated_conditions": evaluated_conditions,
            })
        
        # No default - this is an error
        return StepResult.fail(
            "No route condition matched and no default route configured",
            error_code="NO_MATCHING_ROUTE",
        )
    
    def _evaluate_parallel(
        self,
        routes: list[dict],
        default_route: Optional[str],
        context: EvaluationContext,
    ) -> StepResult:
        """
        Evaluate parallel gateway.
        
        All matching conditions trigger their routes.
        """
        matched_routes = []
        evaluated_conditions = []
        
        for route in routes:
            condition = route.get("condition", "")
            target = route.get("target")
            
            if not target:
                continue
            
            try:
                result = self.condition_evaluator.evaluate(condition, context)
                evaluated_conditions.append({
                    "condition": condition,
                    "target": target,
                    "result": result,
                })
                
                if result:
                    matched_routes.append(target)
                    
            except Exception as e:
                logger.error(f"Error evaluating condition '{condition}': {e}")
                evaluated_conditions.append({
                    "condition": condition,
                    "target": target,
                    "result": False,
                    "error": str(e),
                })
        
        if matched_routes:
            logger.info(f"Parallel gateway matched routes: {matched_routes}")
            return StepResult.ok({
                "routes": matched_routes,
                "gateway_type": "parallel",
                "evaluated_conditions": evaluated_conditions,
            })
        
        # No matches - use default if available
        if default_route:
            logger.info(f"Parallel gateway using default: {default_route}")
            return StepResult.ok({
                "routes": [default_route],
                "gateway_type": "parallel",
                "is_default": True,
                "evaluated_conditions": evaluated_conditions,
            })
        
        return StepResult.fail(
            "No route conditions matched and no default route",
            error_code="NO_MATCHING_ROUTE",
        )
    
    def _evaluate_inclusive(
        self,
        routes: list[dict],
        default_route: Optional[str],
        context: EvaluationContext,
    ) -> StepResult:
        """
        Evaluate inclusive gateway.
        
        All matching conditions plus default (if set).
        Similar to parallel but always includes default.
        """
        # For now, treat same as parallel
        result = self._evaluate_parallel(routes, default_route, context)
        if result.success and result.output:
            result.output["gateway_type"] = "inclusive"
        return result
