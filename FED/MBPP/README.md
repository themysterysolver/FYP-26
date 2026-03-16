# MBPP
- this works for collab version
- the working of windows and jupyter vesrion is done on `NEW_MBPP`
```
MBPP/
│
├── sft_mbpp_output/
│
├── final_dataset_v2.csv
│
├── lora_state_dict.pt
│
├── mbpp_adapter_pipeline_output.csv
│
├── mbpp_pipeline_output.csv
│
├── SFT_LoRA_Adapters.ipynb
│
├── SFT_LoRA_Adapters_op.ipynb
│
├── sft_mbpp_output.zip
│
└── Verify_MBPP_Adapter_Colab_v2.ipynb
```


- **sft_mbpp_output/**  Lora adapters

- **final_dataset_v2.csv**  Processed MBPP dataset used for training or evaluation in the pipeline.

- **lora_state_dict.pt**  Serialized PyTorch file containing the trained LoRA adapter parameters (state dictionary).

- **mbpp_adapter_pipeline_output.csv**  Evaluation results of the MBPP benchmark using the LoRA adapter–enhanced pipeline. 

- **mbpp_pipeline_output.csv**  Baseline MBPP pipeline evaluation results without applying LoRA adapters.

- **SFT_LoRA_Adapters.ipynb**  
Jupyter notebook implementing the LoRA-based supervised fine-tuning process for the MBPP dataset.with improper verfifcation!

- **SFT_LoRA_Adapters_op.ipynb**  
Modified or optimized version of the LoRA SFT notebook used for training and generating adapter outputs.

- **sft_mbpp_output.zip**  Compressed archive containing the full output of the SFT training process.

- **Verify_MBPP_Adapter_Colab_v2.ipynb**  Notebook used to verify and evaluate the trained LoRA adapters on the MBPP dataset in a Google Colab environment.