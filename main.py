import socket
import time

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
def monitor(host: str, port: int = 80, count: int = 10, interval: float = 1.0):
    success_attempts = failed_attempts = total_letancy = 0
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
            total_letancy += end_time - start_time

        except socket.timeout or socket.gaierror or ConnectionRefusedError:
            typer.echo(f"Attempt [{i+1}/{count}]: Failed")

            failed_attempts += 1

        time.sleep(interval)

    typer.echo(f"Success Rate: {(success_attempts/count)*100}%")
    typer.echo(f"Average Letancy: {total_letancy/success_attempts:.3f}s")


if __name__ == "__main__":
    app()
