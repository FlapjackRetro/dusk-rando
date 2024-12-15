using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using MelonLoader;
using UnityEngine;

namespace DuskRando
{
    public class MyFirstMod : MelonMod
    {
        public override void OnInitializeMelon()
        {
            //Here we will add our mod logic
        }

        private float lastTimeLog = 0;
        private float logDelayInSecond = 1f;

        public override void OnUpdate()
        {
            if (Time.time > lastTimeLog + logDelayInSecond)
            {
                lastTimeLog = Time.time;
            }
            else
            {
                return;
            }

            MelonLogger.Msg("Current temperature is: who cares");
        }
    }
}
