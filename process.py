import queue
import random
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from loguru import logger
import threading

import extra
import model


def start():
    extra.show_logo()
    extra.show_dev_info()

    def launch_wrapper(index, proxy, private_key):
        account_flow(lock, index, proxy, private_key, config)

    threads = int(input("\nHow many threads do you want: ").strip())

    config = extra.read_config()
    config["abi"] = extra.read_abi("extra/abi.json")

    proxies = extra.read_txt_file("proxies", "data/proxies.txt")
    private_keys = extra.read_txt_file("private keys", "data/private_keys.txt")
    indexes = [i + 1 for i in range(len(private_keys))]
    mobile_proxy_queue = queue.Queue()

    if config["shuffle_accounts"]:
        combined = list(zip(indexes, proxies, private_keys))
        random.shuffle(combined)
        indexes, proxies, private_keys = zip(*combined)

    use_proxy = True
    if len(proxies) == 0:
        if not extra.no_proxies():
            return
        else:
            use_proxy = False

    lock = threading.Lock()

    if config["mobile_proxy"].lower() == "yes":
        ip_change_links = extra.read_txt_file(
            "ip change links", "data/ip_change_links.txt"
        )

        for i in range(len(private_keys)):
            mobile_proxy_queue.put(i)
        cycle = []
        for i in range(len(proxies)):
            data_list = (
                proxies[i],
                ip_change_links[i],
                mobile_proxy_queue,
                config,
                lock,
                private_keys,
            )
            cycle.append(data_list)

        logger.info("Starting...")
        with ThreadPoolExecutor() as executor:
            executor.map(mobile_proxy_wrapper, cycle)

        logger.success("Saved accounts and private keys to a file.")
        return

    else:
        if not use_proxy:
            proxies = ["" for _ in range(len(private_keys))]
        elif len(proxies) < len(private_keys):
            proxies = [proxies[i % len(proxies)] for i in range(len(private_keys))]

    logger.info("Starting...")
    with ThreadPoolExecutor(max_workers=threads) as executor:
        executor.map(launch_wrapper, indexes, proxies, private_keys)

    logger.success("Saved accounts and private keys to a file.")


def account_flow(
    lock: threading.Lock, account_index: int, proxy: str, private_key: str, config: dict
):
    try:
        xterio_instance = model.xterio.Xterio(private_key, proxy, config)

        ok = wrapper(xterio_instance.init_instance, 1)
        if not ok:
            raise Exception("unable to init xterio instance")

        ok = wrapper(xterio_instance.complete_all_tasks, 1)
        if not ok:
            raise Exception("unable to complete all tasks")

        with lock:
            with open("data/success_data.txt", "a") as f:
                f.write(f"{private_key}:{proxy}\n")

        time.sleep(
            random.randint(
                config["pause_between_accounts"][0], config["pause_between_accounts"][1]
            )
        )
        logger.success(f"{account_index} | Account flow completed successfully")

    except Exception as err:
        logger.error(f"{account_index} | Account flow failed: {err}")
        with lock:
            report_failed_key(private_key, proxy)


def wrapper(function, attempts: int, *args, **kwargs):
    for _ in range(attempts):
        result = function(*args, **kwargs)
        if isinstance(result, tuple) and result and isinstance(result[0], bool):
            if result[0]:
                return result
        elif isinstance(result, bool):
            if result:
                return True

    return result


def report_failed_key(private_key: str, proxy: str):
    try:
        with open("data/failed_keys.txt", "a") as file:
            file.write(private_key + ":" + proxy + "\n")

    except Exception as err:
        logger.error(f"Error while reporting failed account: {err}")


def mobile_proxy_wrapper(data):
    proxy, ip_change_link, mobile_proxy_queue, config, lock, private_keys = data[:7]

    while not mobile_proxy_queue.empty():
        i = mobile_proxy_queue.get()

        try:
            for _ in range(3):
                try:
                    requests.get(
                        f"{ip_change_link}",
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        },
                        timeout=60,
                    )

                    time.sleep(config["change_ip_pause"])
                    logger.success(f"{i + 1} | Successfully changed IP")
                    break

                except Exception as err:
                    logger.error(
                        f"{i + 1} | Mobile proxy error! Check your ip change link: {err}"
                    )
                    time.sleep(2)

            account_flow(lock, i + 1, proxy, private_keys[i], config)

        except Exception as err:
            logger.error(f"{i + 1} | Mobile proxy flow error: {err}")
