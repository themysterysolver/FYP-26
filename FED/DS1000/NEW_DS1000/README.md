## DS1000

```
NEW_DS1000/
│
├── lora_adapters/ 
│
├── lora_adapters_100/
│
├── ds1000_adapter_pipeline_output.csv
│
├── ds1000_adapter_pipeline_output_1.csv
│
├── ds1000_pipeline_output.csv
│
├── README.md
│
├── SFT_LoRA_Adapters_Windows.ipynb
│
└── Verify_DS1000_Adapter_Windows.ipynb
```

- **lora_adapters/**   Contains the generated LoRA adapter weights produced during fine-tuning all DS1K dataset.

- **lora_adapters_100/**  only for 100 datas

- **ds1000_adapter_pipeline_output.csv**  - output for everything 1k

- **ds1000_adapter_pipeline_output_1.csv**  - output for 100 datas

- **ds1000_pipeline_output.csv**  - baseline

- **SFT_LoRA_Adapters_Windows.ipynb**  - Jupyter notebook used to perform Supervised Fine-Tuning (SFT) and generate LoRA adapters on a Windows environment.

- **Verify_DS1000_Adapter_Windows.ipynb**  - Notebook used to verify and evaluate the generated LoRA adapters on the DS1000 dataset.