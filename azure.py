import logging
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.monitor.models import ResultType
from datetime import datetime, timedelta

def main(mytimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function processed a timer event.')

    # Subskrypcja ID oraz Resource Group
    subscription_id = 'your-subscription-id'
    resource_group = 'your-resource-group'
    vmss_names = ['vmss1', 'vmss2']  # Nazwy VMSS
    cpu_threshold = 10  # CPU Threshold
    memory_threshold = 20  # Memory Threshold

    # Crednetials oraz inicializacja
    credential = DefaultAzureCredential()
    compute_client = ComputeManagementClient(credential, subscription_id)
    monitor_client = MonitorManagementClient(credential, subscription_id)

    for vmss_name in vmss_names:

        # CPU i Memory -zuzycie w VMSS w 30 minut
        now = datetime.now()
        metrics_data = monitor_client.metrics.list(
            f'subscriptions/{subscription_id}/resourceGroups/{resource_group}'
            f'/providers/Microsoft.Compute/virtualMachineScaleSets/{vmss_name}',
            timespan=f"{(now-timedelta(minutes=30)).isoformat()}/{now.isoformat()}",
            interval='PT1M',
            metricnames='Percentage CPU,Memory',
            aggregation='Average',
            result_type=ResultType.DATA
        )

        # srednia CPU i memory
        for metric in metrics_data.value:
            if metric.name.value == "Percentage CPU":
                cpu_usage = [item.average for time_series in metric.timeseries for item
                             in time_series.data]
                avg_cpu_usage = sum(cpu_usage) / len(cpu_usage)
            elif metric.name.value == "Memory":
                memory_usage = [item.average for time_series in metric.timeseries for
                                item in time_series.data]
                avg_memory_usage = sum(memory_usage) / len(memory_usage)

        # Jesli srednia uzycia CPU i Memory jest ponizej normy, wylacz VMSS
        if avg_cpu_usage < cpu_threshold and avg_memory_usage < memory_threshold:
            try:
                compute_client.virtual_machine_scale_sets.power_off(resource_group,
                                                                    vmss_name)
                logging.info(f"VMSS {vmss_name} shutdown successful.")
            except Exception as e:
                logging.error(f"An error occurred while shutting down {vmss_name}: "
                              f"{str(e)}")
        else:
            logging.info(f"VMSS {vmss_name} usage is above threshold, not shutting down.")

    logging.info("VMSS management operation completed.")
