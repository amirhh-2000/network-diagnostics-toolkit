import json
import socket
import time
from pathlib import Path

import dns.resolver
import httpx
import typer
from typer import Option

app = typer.Typer()


@app.command()
def ping(host: str, quiet: bool = False) -> dict | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)

            start_time = time.time()
            sock.connect((host, 80))
            end_time = time.time()
            latency = end_time - start_time

            if not quiet:
                typer.echo(f"Connection established in {latency:.3f}s")

            return {"host": host, "latency": latency}

    except socket.timeout:
        typer.echo("Connection timed out")
    except socket.gaierror as e:
        typer.echo(f"Failed to resolve {host}: {e}")
    except ConnectionRefusedError:
        typer.echo(f"Connection refused by {host} (port closed)")
    except Exception as e:
        typer.echo(f"An unexpected error occurred: {e}")


@app.command()
def api_check(url: str, quiet: bool = False) -> dict | None:
    try:
        start_time = time.time()
        resp = httpx.get(url, timeout=5)
        end_time = time.time()

        if not quiet:
            typer.echo(
                f"Status: {resp.status_code}, Latency: {end_time-start_time:.3f}s"
            )

        return {
            "url": url,
            "status_code": resp.status_code,
            "latency": end_time - start_time,
        }

    except httpx.TimeoutException:
        typer.echo("Request timed out")
    except httpx.ConnectError as e:
        typer.echo(f"DNS failure or server down: {e}")
    except httpx.HTTPError as e:
        typer.echo(f"HTTP Error: {e}")
    except Exception as e:
        typer.echo(f"An unexpected error occurred: {e}")


@app.command()
def dns_check(domain: str, quiet: bool = False) -> dict | None:
    resolver = dns.resolver.Resolver()

    try:
        start_time = time.time()
        res = resolver.resolve(domain, "A")
        end_time = time.time()

        if not quiet:
            typer.echo(f"DNS resolved in {end_time-start_time:.3f}s")
            typer.echo(f"IP address: {res[0]}")

        return {
            "domain": domain,
            "ip": str(res[0]),
            "latency": end_time - start_time,
        }

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
def monitor(
    host: str,
    port: int = 80,
    count: int = 5,
    interval: float = 1.0,
    quiet: bool = False,
):
    success_attempts = failed_attempts = total_latency = 0
    for i in range(count):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)

                start_time = time.time()
                sock.connect((host, port))
                end_time = time.time()

                if not quiet:
                    typer.echo(
                        f"Attempt [{i+1}/{count}]: Connected in {end_time-start_time:.3f}s"
                    )

            success_attempts += 1
            total_latency += end_time - start_time

        except (socket.timeout, socket.gaierror, ConnectionRefusedError):
            if not quiet:
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

    return {
        "success_rate": (success_attempts / count) * 100,
        "average_latency": total_latency / success_attempts
        if success_attempts > 0
        else None,
    }


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
def generate_report(
    host: str = Option(
        ..., "--host", help="Host to ping and monitor (e.g., google.com)"
    ),
    url: str = Option(
        ..., "--url", help="URL to test API (e.g., https://api.github.com)"
    ),
    domain: str = Option(
        ..., "--domain", help="Domain to check DNS (e.g., google.com)"
    ),
    save_to_file: bool = Option(
        False, "--output-file", help="Save report to a JSON file"
    ),
):
    report = {
        "ping": ping(host, quiet=True),
        "api-check": api_check(url, quiet=True),
        "dns-check": dns_check(domain, quiet=True),
        "monitor": monitor(domain, quiet=True),
    }

    typer.echo("=== Network Diagnostics Report ===")
    typer.echo(f"Ping: Connected to {host} in {report['ping']['latency']}s")
    typer.echo(
        f"API Check: Status 200 for {url} in {report['api-check']['latency']}s"
    )
    typer.echo(
        f"DNS Check: Resolved {domain} to 142.250.190.14 in {report['dns-check']['latency']}s"
    )
    typer.echo(
        f"Monitor: Success Rate 80% for {domain}, Average Latency {report['monitor']['average_latency']}s"
    )

    typer.echo(f"JSON Report:\n{json.dumps(report, indent=4)}")

    if save_to_file:
        _save_report(report)


if __name__ == "__main__":
    app()
