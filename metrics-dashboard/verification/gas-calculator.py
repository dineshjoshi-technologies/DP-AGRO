#!/usr/bin/env python3
"""Gas cost calculator for AI-Agriculture blockchain audit trail (DPA-84).

Estimates gas costs for the smart contract functions defined in
DPA-84#document-metrics-audit-trail-spec §2.2.

Usage:
    python3 gas-calculator.py --events 1000 --batch-size 50 --gas-price-gwei 20
    python3 gas-calculator.py --events 1000 --batch-size 50 --gas-price-gwei 20 --output report.json

Output includes:
    - Per-function gas estimates
    - Total weekly gas cost in ETH and USD (configurable)
    - Batch optimization savings vs single writes
"""

import argparse
import json
import math
import sys


# Gas costs per operation (approximate, based on Ethereum mainnet)
GAS_COSTS = {
    "log_sensor_batch": 65000,       # EmitLogSensorBatch
    "log_model_training": 80000,     # EmitLogModelTraining
    "log_model_promotion": 70000,    # EmitLogModelPromotion
    "log_predictions_batch": 55000,  # EmitLogPredictions (single)
    "batch_write_with_merkle": 120000,  # Batch write with merkle root
    "verify_schema_compliance": 25000,  # View function (no gas on-chain, estimate for L2)
}

# Per-event overhead for batching (merkle tree computation)
MERCLE_TREE_OVERHEAD_PER_LEVEL = 10000  # gas per node in merkle tree


def estimate_gas(events, batch_size=None):
    """Estimate gas for a given number of events with optional batching."""
    total_events = events
    if batch_size is None:
        batch_size = total_events  # No batching

    # Categorize event types (assume uniform distribution for estimation)
    event_types = ["sensor_batch_ingest", "model_training", "model_promotion", "prediction_batch"]
    events_per_type = total_events // len(event_types)

    total_gas = 0
    breakdown = {}

    for etype in event_types:
        gas_per_event = GAS_COSTS.get(f"log_{etype.replace('_', '')}", 65000)

        if batch_size >= total_events:
            # No batching: each event is a separate write
            gas = gas_per_event * events_per_type
            label = f"single_{etype}"
        else:
            # Batching: group events into batches
            num_batches = (events_per_type + batch_size - 1) // batch_size
            # Each batch write costs more due to merkle tree computation
            batch_gas = GAS_COSTS["batch_write_with_merkle"]
            # Add merkle tree overhead
            tree_levels = max(1, int(math.ceil(math.log2(batch_size))))
            merkle_overhead = MERCLE_TREE_OVERHEAD_PER_LEVEL * tree_levels * num_batches
            gas = batch_gas * num_batches + merkle_overhead
            label = f"batched_{etype}"

        total_gas += gas
        breakdown[label] = {
            "events": events_per_type,
            "batches": num_batches if batch_size < total_events else 1,
            "gas": gas,
        }

    return total_gas, breakdown


def calculate_cost(gas, gas_price_gwei, eth_price_usd=None):
    """Calculate USD cost from gas units."""
    gas_in_wei = gas * 1_000_000_000  # Convert Gwei to Wei
    eth_cost = gas_in_wei / 1_000_000_000_000_000_000  # Convert Wei to ETH
    usd_cost = eth_cost * gas_price_gwei if eth_price_usd is None else eth_cost * eth_price_usd

    return {
        "gas_units": gas,
        "gas_price_gwei": gas_price_gwei,
        "eth_cost": round(eth_cost, 6),
        "usd_cost": round(usd_cost, 2) if eth_price_usd else None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Gas cost calculator (DPA-84, spec §2.3)"
    )
    parser.add_argument("--events", type=int, default=1000, help="Number of events per week")
    parser.add_argument("--batch-size", type=int, default=50, help="Events per batch write")
    parser.add_argument("--gas-price-gwei", type=float, default=20, help="Gas price in Gwei")
    parser.add_argument("--eth-price-usd", type=float, default=None, help="ETH price in USD (optional)")
    parser.add_argument("--output", help="Write report to JSON file")
    args = parser.parse_args()

    # Calculate single vs batched costs
    gas_single, breakdown_single = estimate_gas(args.events, batch_size=None)
    gas_batched, breakdown_batched = estimate_gas(args.events, batch_size=args.batch_size)

    cost_single = calculate_cost(gas_single, args.gas_price_gwei, args.eth_price_usd)
    cost_batched = calculate_cost(gas_batched, args.gas_price_gwei, args.eth_price_usd)

    savings = cost_single["eth_cost"] - cost_batched["eth_cost"]
    savings_pct = (savings / cost_single["eth_cost"] * 100) if cost_single["eth_cost"] > 0 else 0

    report = {
        "parameters": {
            "events_per_week": args.events,
            "batch_size": args.batch_size,
            "gas_price_gwei": args.gas_price_gwei,
            "eth_price_usd": args.eth_price_usd,
        },
        "single_write": {
            "gas_units": gas_single,
            "eth_cost": cost_single["eth_cost"],
            "usd_cost": cost_single["usd_cost"],
            "breakdown": breakdown_single,
        },
        "batched_write": {
            "gas_units": gas_batched,
            "eth_cost": cost_batched["eth_cost"],
            "usd_cost": cost_batched["usd_cost"],
            "breakdown": breakdown_batched,
        },
        "savings": {
            "eth_saved": round(savings, 6),
            "usd_saved": round(savings * args.gas_price_gwei, 2) if args.eth_price_usd else None,
            "savings_pct": round(savings_pct, 1),
        },
        "weekly_projection": {
            "estimated_weekly_gas": gas_batched,
            "estimated_weekly_eth": cost_batched["eth_cost"],
            "estimated_monthly_eth": round(cost_batched["eth_cost"] * 4, 6),
            "estimated_annual_eth": round(cost_batched["eth_cost"] * 52, 6),
        },
    }

    if args.output:
        with open(args.output, "w") as fp:
            json.dump(report, fp, indent=2)
        print(f"Report written to {args.output}")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
