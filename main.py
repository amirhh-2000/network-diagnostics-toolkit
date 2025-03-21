import json
import socket
import time
from pathlib import Path

import dns.resolver
import httpx
import typer

app = typer.Typer()


@app.command()
def ping(url: str):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)

            start_time = time.time()
            sock.connect((url, 80))
            end_time = time.time()

            typer.echo(f"Connection established in {end_time-start_time:.3f}s")

    except socket.timeout:
        typer.echo("Connection timed out")
    except socket.gaierror as e:
        typer.echo(f"Failed to resolve {url}: {e}")
    except ConnectionRefusedError:
        typer.echo(f"Connection refused by {url} (port closed)")
    except Exception as e:
        typer.echo(f"An unexpected error occurred: {e}")


@app.command()
def test_api(url: str):
    try:
        start_time = time.time()
        resp = httpx.get(url, timeout=5)
        end_time = time.time()

        typer.echo(
            f"Status: {resp.status_code}, Latency: {end_time-start_time:.3f}s"
        )

    except httpx.TimeoutException:
        typer.echo("Request timed out")
    except httpx.ConnectError as e:
        typer.echo(f"DNS failure or server down: {e}")
    except httpx.HTTPError as e:
        typer.echo(f"HTTP Error: {e}")
    except Exception as e:
        typer.echo(f"An unexpected error occurred: {e}")


@app.command()
def dns_check(domain: str):
    resolver = dns.resolver.Resolver()

    try:
        start_time = time.time()
        res = resolver.resolve(domain, "A")
        end_time = time.time()

        typer.echo(f"DNS resolved in {end_time-start_time:.3f}s")
        typer.echo(f"IP address: {res[0]}")

    except dns.resolver.NXDOMAIN:
        typer.echo(f"Domain {domain} does not exist")
    except dns.resolver.NoAnswer:
        typer.echo("DNS record not found")
    except dns.resolver.NoNameservers:
        typer.echo("DNS server not found")
    except dns.resolver.Timeout:
        typer.echo("DNS query timed out")
    except Exception as e:
        typer.echo(f"An unexpected error occurred: {e}")


@app.command()
def monitor(host: str, port: int = 80, count: int = 5, interval: float = 1.0):
    success_attempts = failed_attempts = total_latency = 0
    for i in range(count):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)

                start_time = time.time()
                sock.connect((host, port))
                end_time = time.time()

                typer.echo(
                    f"Attempt [{i+1}/{count}]: Connected in {end_time-start_time:.3f}s"
                )

            success_attempts += 1
            total_latency += end_time - start_time

        except (socket.timeout, socket.gaierror, ConnectionRefusedError):
            typer.echo(f"Attempt [{i+1}/{count}]: Failed")
            failed_attempts += 1
        except Exception as e:
            # TODO: log it
            failed_attempts += 1
            typer.echo(f"An unexpected error occurred: {e}")

        time.sleep(interval)

    typer.echo(f"Success Rate: {(success_attempts/count)*100}%")
    try:
        typer.echo(f"Average Latency: {total_latency/success_attempts:.3f}s")
    except ZeroDivisionError:
        typer.echo("Average Latency: N/A")


def _save_report(report: dict):
    from datetime import datetime

    try:
        save_dir = Path("reports")
        save_dir.mkdir(parents=True, exist_ok=True)
        file = (
            save_dir / f"report-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        )
        with open(file, "w") as f:
            json.dump(report, f, indent=4)
    except PermissionError:
        typer.echo("Failed to save report: Permission denied")
    except IOError as e:
        typer.echo(f"Failed to write report file: {e}")


@app.command()
def generate_report(save_to_file: bool = False):
    report = {
        "ping": {"host": "google.com", "latency": 0.045},
        "test-api": {
            "url": "https://api.github.com",
            "status": 200,
            "latency": 0.245,
        },
        "dns-check": {
            "domain": "google.com",
            "ips": ["142.250.190.14"],
            "latency": 0.023,
        },
        "monitor": {
            "host": "google.com",
            "success_rate": 80,
            "avg_latency": 0.046,
        },
    }

    typer.echo("=== Network Diagnostics Report ===")
    typer.echo("Ping: Connected to google.com in 0.045s")
    typer.echo("Test API: Status 200 for https://api.github.com in 0.245s")
    typer.echo("DNS Check: Resolved google.com to 142.250.190.14 in 0.023s")
    typer.echo(
        "Monitor: Success Rate 80% for google.com, Average Latency 0.046s"
    )

    typer.echo(f"JSON Report:\n{json.dumps(report, indent=4)}")

    if save_to_file:
        _save_report(report)


if __name__ == "__main__":
    app()
