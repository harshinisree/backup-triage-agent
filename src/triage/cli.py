import argparse
import json

import pandas as pd

from .agent import TriageAgent
from .anomaly import detect
from .models import Incident


def main() -> None:
    p = argparse.ArgumentParser(prog="triage")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("triage")
    t.add_argument("message")
    t.add_argument("--id", default="INC-CLI")
    t.add_argument("--host", default="unknown")
    a = sub.add_parser("anomalies")
    a.add_argument("csv")
    args = p.parse_args()

    if args.cmd == "triage":
        res = TriageAgent().triage(Incident(args.id, args.message, args.host))
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(detect(pd.read_csv(args.csv)).to_string(index=False))


if __name__ == "__main__":
    main()
